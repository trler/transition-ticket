import base64
import json
import struct
from random import randint
from time import time

from loguru import logger

from util.Info import Info
from util.Request import Request


class Bilibili:
    """
    会员购
    """

    @logger.catch
    def __init__(
        self,
        net: Request,
        projectId: int,
        linkId: int,
        screenId: int,
        skuId: int,
        saleStart: int,
        count: int,
        cost: int,
        deliverFee: int,
        needDeliver: bool,
        needContact: bool,
        bind: int,
        package: dict,
        act: dict,
        buyer: dict,
        deliver: dict,
        phone: str,
        user: dict,
        orderType: int = 1,
    ):
        """
        初始化

        net: 网络实例
        projectId: 项目ID
        linkId: 商品ID
        screenId: 场次ID
        skuId: 票种ID
        saleStart: 开始时间戳
        count: 购买数量
        cost: 订单单价
        deliverFee: 运费
        needDeliver: 是否需要填写收货信息
        needContact: 是否需要填写联系人信息
        bind: ID绑定类型
        package: 包裹信息
        act: 优惠信息
        buyer: 购买者信息
        deliver: 收货信息
        phone: 手机号
        user: 用户信息
        orderType: 订单类型
        """
        self.net = net
        self.info = Info(net=net)

        self.scene = "neul-next"
        self.version = "1.1.0"
        self.coupon = ""

        # Order Params
        self.projectId = projectId
        self.linkId = linkId
        self.screenId = screenId
        self.skuId = skuId
        self.count = count
        self.cost = cost
        self.deliverFee = deliverFee
        self.saleStart = saleStart

        self.payment = self.count * self.cost + self.deliverFee

        self.isHot = False
        self.needDeliver = needDeliver
        self.needContact = needContact
        self.bind = bind
        self.package = package
        self.act = act
        self.buyer = buyer
        self.phone = phone
        self.deliver = deliver
        self.user = user

        self.orderType = orderType
        self.orderId = 0
        self.orderToken = ""
        self.token = ""
        self.ptoken = ""
        self.risked = False
        self.prepareTime = 0
        self.ctoken = ""

        # Risk Param
        self.buvid = ""
        self.decisionType = ""
        self.ip = ""
        self.mid = ""
        self.ua = ""
        self.voucher = ""
        self.challenge = ""
        self.gt = ""

    @logger.catch
    def RiskInfo(self) -> tuple[int, str, str, str]:
        """
        获取流水
        """
        url = "https://api.bilibili.com/x/gaia-vgate/v1/register"
        params = {
            "buvid": self.buvid,
            "csrf": self.net.GetCookie()["bili_jct"],
            "decision_type": self.decisionType,
            "ip": self.ip,
            "mid": self.mid,
            "origin_scene": self.scene,
            "scene": self.scene,
            "ua": self.ua,
            "v_voucher": self.voucher,
        }
        res = self.net.Response(method="post", url=url, params=params)
        code = res["code"]
        msg = res["message"]

        match code:
            # 成功
            case 0:
                data = res["data"]
                self.token = data["token"]
                type = data["type"]

                match type:
                    case "geetest":
                        self.challenge = data["geetest"]["challenge"]
                        self.gt = data["geetest"]["gt"]
                        dist = self.challenge
                    case "phone":
                        dist = data["phone"]["tel"]
                    case _:
                        dist = ""
            case _:
                type = ""
                dist = ""

        return code, msg, type, dist

    @logger.catch
    def RiskValidate(self, val: str = "", mode: str = "geetest") -> tuple[int, str]:
        """
        校验

        val: 校验值
        mode: 验证方式
        """
        url = "https://api.bilibili.com/x/gaia-vgate/v1/validate"

        match mode:
            case "geetest":
                params = {
                    "challenge": self.challenge,
                    "csrf": self.net.GetCookie()["bili_jct"],
                    "seccode": val + "|jordan",
                    "token": self.token,
                    "validate": val,
                }
            case "phone":
                params = {
                    "code": self.phone,
                    "csrf": self.net.GetCookie()["bili_jct"],
                    "token": self.token,
                }
            case _:
                params = {}
                logger.error("【验证】这是什么验证类型?")

        res = self.net.Response(method="get", url=url, params=params)
        code = res["code"]
        msg = res["message"]

        # 成功&有效
        if code == 0 and res["data"]["is_valid"] == 1:
            self.risked = True
            cookie = self.net.GetCookie()
            cookie["x-bili-gaia-vtoken"] = self.token
            self.net.RefreshCookie(cookie)

        return code, msg

    @logger.catch
    def QueryToken(self) -> tuple[int, str]:
        """
        获取Token
        """
        # 成功
        if not self.risked:
            url = f"https://show.bilibili.com/api/ticket/order/prepare?project_id={self.projectId}"

        # 刚刚验证完
        else:
            url = f"https://show.bilibili.com/api/ticket/order/prepare?project_id={self.projectId}&token={self.token}&gaia_vtoken={self.token}"
            self.risked = False

        params = {
            "project_id": self.projectId,
            "screen_id": self.screenId,
            "sku_id": self.skuId,
            "count": self.count,
            "order_type": self.orderType,
            "token": "",
            "requestSource": self.scene,
            "newRisk": True,
        }
        res = self.net.Response(method="post", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 成功
            case 0:
                self.prepareTime = int(time() * 1000)
                self.token = res["data"]["token"]
                if self.isHot:
                    self.ptoken = res["data"]["ptoken"]

            # 验证
            case -401:
                riskParams = res["data"]["ga_data"]["riskParams"]
                self.mid = riskParams["mid"]
                self.decisionType = riskParams["decision_type"]
                self.buvid = riskParams["buvid"]
                self.ip = riskParams["ip"]
                self.scene = riskParams["scene"]
                self.ua = riskParams["ua"]
                self.voucher = riskParams["v_voucher"]

        return code, msg

    @logger.catch
    def GenerateToken(self) -> tuple[int, str]:
        """
        生成Token

        Base64: URLSafeBase64
        """
        token = bytes([192])

        token += b"\x7f\xff\xff\xff"
        # token += int(time()).to_bytes(4)
        token += self.projectId.to_bytes(4)
        token += self.screenId.to_bytes(4)
        token += self.orderType.to_bytes(1)
        token += self.count.to_bytes(2)
        token += self.skuId.to_bytes(4)

        token = base64.urlsafe_b64encode(token).decode()

        self.token = token
        return 0, token

    @logger.catch
    def QueryStartTime(self) -> tuple[int, str, int]:
        """
        获取开票时间
        """
        saleStart = self.info.QuerySaleStart(
            projectId=self.projectId,
            linkId=self.linkId,
            screenId=self.screenId,
            skuId=self.skuId,
            cost=self.cost,
        )

        interval = self.info.QueryTimestamp() - time()
        saleStart = saleStart - interval
        logger.info(f"【开票时间】已校准时间差为: {interval:.3f} 秒")

        return 0, "", saleStart

    @logger.catch
    def QueryAmount(self) -> tuple[int, str, bool, int, int]:
        """
        获取票数
        """
        code, msg, skuInfo = self.info.QuerySku(
            projectId=self.projectId,
            linkId=self.linkId,
            screenId=self.screenId,
            skuId=self.skuId,
            cost=self.cost,
        )

        match code:
            # 成功
            case 0:
                clickable = skuInfo["clickable"]
                salenum = skuInfo["salenum"]
                num = skuInfo["num"]
            case _:
                clickable = False
                salenum = 4
                num = 0

        return code, msg, clickable, salenum, num

    @logger.catch
    def CreateOrder(self) -> tuple[int, str]:
        """
        创建订单
        """
        url = "https://show.bilibili.com/api/ticket/order/createV2"
        timestamp = int(round(time() * 1000))
        clickPosition = {
            # "x": randint(1300, 1500),
            "x": randint(600, 1000),
            # "y": randint(20, 100),
            "y": randint(2400, 2500),
            # "origin": timestamp - randint(1500, 10000),
            "origin": max(self.saleStart * 1000, timestamp - randint(1500, 10000)),
            "now": timestamp,
        }
        params = {
            "project_id": self.projectId,
            "screen_id": self.screenId,
            "sku_id": self.skuId,
            "count": self.count,
            "pay_money": self.payment,
            "order_type": self.orderType,
            "timestamp": timestamp,
            "buyer_info": json.dumps(self.buyer),
            "token": self.token,
            "deviceId": self.net.GetCookie()["deviceFingerprint"],
            "clickPosition": clickPosition,
            "requestSource": self.scene,
            "id_bind": self.bind,
            "is_package": self.package["is_package"],
            "package_num": self.package["package_num"],
            "coupon_code": self.coupon,
            "version": self.version,
            "again": 1,
            "newRisk": True,
        }
        if self.isHot:
            params["ptoken"] = self.ptoken
            params["ctoken"] = self.EncodeCtoken()

        # 优惠票
        if self.act:
            params["act_id"] = self.act["act_id"]
            params["order_type"] = self.act["act_type"]

        # 邮寄票
        if self.needDeliver:
            params["deliver_info"] = json.dumps(self.deliver, ensure_ascii=False)
            params["buyer"] = self.user["username"]
            params["tel"] = self.phone

        # 联系人信息
        if self.needContact:
            params["buyer"] = self.user["username"]
            params["tel"] = self.phone

        # 场贩
        if self.linkId:
            params["link_id"] = self.linkId

        res = self.net.Response(method="post", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 成功
            case 0:
                self.orderId = res["data"]["orderId"]
                self.orderToken = res["data"]["token"]

            # 存在订单
            case 100079:
                self.orderId = res["data"]["orderId"]

            # 票价错误
            case 100034:
                self.payment = res["data"]["pay_money"]

            # 未预填联系人信息
            case 209001:
                self.needContact = True

            # 未预填收货信息
            case 214:
                self.needDeliver = True

        return code, msg

    @logger.catch
    def CreateOrderStatus(self) -> tuple[int, str]:
        """
        创建订单状态
        """
        url = "https://show.bilibili.com/api/ticket/order/createstatus"
        params = {
            "token": self.orderToken,
            "project_id": self.projectId,
            "orderId": self.orderId,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 100012: 订单未完成
            case 100012:
                # 订单ID相同, 说明订单已经创建
                if res["data"]["order_id"] == self.orderId:
                    code = 0

            # 100040: 0元订单
            case 100040:
                code = 0

        return code, msg

    @logger.catch
    def QueryOrderStatus(self) -> tuple[int, str]:
        """
        获取订单状态
        """
        url = "https://show.bilibili.com/api/ticket/order/info"
        params = {
            "order_id": self.orderId,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        return code, msg

    @logger.catch
    def EncodeCtoken(self) -> str:
        current_time_ms = int(time() * 1000)
        calculatedTime = (current_time_ms - self.prepareTime) / 1000
        secFromPrepare = int(calculatedTime)
        if secFromPrepare <= 0:
            secFromPrepare = 1

        scrollX = 0
        scrollY = 0
        innerWidth = 1800
        innerHeight = 1038
        outerWidth = 1800
        outerHeight = 1125
        screenX = 0
        screenY = 44
        screenWidth = 1800

        data = bytearray(16)
        data[0] = 0
        data[1] = min(scrollX, 255)
        data[2] = 0
        data[3] = min(scrollY, 255)
        data[4] = min(innerWidth, 255)
        data[5] = 1
        data[6] = min(innerHeight, 255)
        data[7] = min(outerWidth, 255)
        struct.pack_into('>H', data, 8, min(secFromPrepare, 65535))
        struct.pack_into('>H', data, 10, min(int(calculatedTime), 65535))
        data[12] = min(outerHeight, 255)
        data[13] = min(screenX, 255)
        data[14] = min(screenY, 255)
        data[15] = min(screenWidth, 255)

        char_string = ''.join(chr(b) for b in data)
        uint16_array = []
        for char in char_string:
            uint16_array.append(ord(char))
        uint8_array = bytearray()
        for value in uint16_array:
            uint8_array.extend(struct.pack('<H', value))

        return base64.b64encode(uint8_array).decode('ascii')
