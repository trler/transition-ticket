from loguru import logger

from util.Request import Request


class InfoException(Exception):
    """
    信息错误
    """

    def __init__(self, title: str, message: str):
        self.title = title
        self.message = message
        logger.error(f"【{title}】{message}")


class Info:
    """
    信息
    """

    @logger.catch
    def __init__(self, net: Request):
        """
        初始化

        net: 网络实例
        """
        self.net = net

        self.scene = "neul-next"

    def Project(self, projectId: int) -> tuple[int, str, dict]:
        """
        项目基本信息

        projectId: 项目ID
        """
        url = "https://show.bilibili.com/api/ticket/project/getV2"
        params = {
            "version": "134",
            "id": projectId,
            "project_id": projectId,
            "requestSource": self.scene,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 成功
            case 0:
                base = 0
                for i, item in enumerate(res["data"]["performance_desc"]["list"]):
                    if item["module"] == "base_info":
                        base = i
                        break
                dist = {
                    "id": res["data"]["id"],
                    "name": res["data"]["name"],
                    "time": res["data"]["performance_desc"]["list"][base]["details"][0]["content"],
                    "need_deliver": res["data"]["has_paper_ticket"],
                    "need_contact": res["data"]["need_contact"],
                }
            case _:
                dist = {}

        return code, msg, dist

    def ScreenList(self, projectId: int) -> tuple[int, str, list[dict]]:
        """
        场次信息列表

        projectId: 项目ID
        """
        url = "https://show.bilibili.com/api/ticket/project/getV2"
        params = {
            "version": "134",
            "id": projectId,
            "project_id": projectId,
            "requestSource": self.scene,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 成功
            case 0:
                screens = res["data"]["screen_list"]
                if not screens:
                    raise InfoException("活动详情", "该活动暂未开放票务信息")

                dist = []
                for screen in screens:
                    dist.append(
                        {
                            "id": screen["id"],
                            "name": screen["name"],
                            "display_name": screen["saleFlag"]["display_name"],
                            "sale_start": screen["sale_start"],
                            "sale_end": screen["sale_end"],
                            "express_fee": screen["express_fee"],
                        }
                    )
            case _:
                dist = []
        return code, msg, dist

    def SkuList(self, projectId: int, screenId: int) -> tuple[int, str, list[dict]]:
        """
        票种信息列表

        screenId: 场次ID
        """
        url = "https://show.bilibili.com/api/ticket/project/getV2"
        params = {
            "version": "134",
            "id": projectId,
            "project_id": projectId,
            "requestSource": self.scene,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 成功
            case 0:
                for i in res["data"]["screen_list"]:
                    if i["id"] == screenId:
                        skus = i["ticket_list"]
                        break

                dist = []
                for sku in skus:
                    dist.append(
                        {
                            "id": sku["id"],
                            "name": f"{sku['screen_name']} - {sku['desc']}",
                            "display_name": sku["sale_flag"]["display_name"],
                            "price": sku["price"],
                            "display_price": f"{(sku['price'] / 100):.2f}",
                            "sale_start": sku["saleStart"],
                            "sale_end": sku["saleEnd"],
                            "clickable": sku["clickable"],
                            "salenum": sku["sale_flag_number"],
                            "num": sku["num"],
                            "act": {
                                "act_id": sku["discount_act"]["act_id"],
                                "act_type": sku["discount_act"]["act_type"],
                            }
                            if sku["discount_act"]
                            else {},
                        }
                    )
            case _:
                dist = []
        return code, msg, dist

    def Screen(self, projectId: int, screenId: int) -> dict:
        """
        场次信息

        projectId: 项目ID
        screenId: 场次ID
        """
        _, _, screens = self.ScreenList(projectId=projectId)

        for screen in screens:
            if screen["id"] == screenId:
                return screen
        raise InfoException("场次查询", "指定场次不存在")

    def Sku(self, projectId: int, screenId: int, skuId: int, cost: int) -> dict:
        """
        票种信息

        projectId: 项目ID
        screenId: 场次ID
        skuId: 票档ID
        cost: 价格
        """
        _, _, skus = self.SkuList(projectId=projectId, screenId=screenId)

        for sku in skus:
            if sku["id"] == skuId and sku["price"] == cost:
                return sku
        raise InfoException("场次查询", "指定票种不存在")

    def Buyer(self) -> list:
        """
        购买人

        接口: GET https://show.bilibili.com/api/ticket/buyer/list?is_default&projectId=${projectId}
        """
        res = self.net.Response(
            method="get",
            url="https://show.bilibili.com/api/ticket/buyer/list",
        )

        lists = res["data"]["list"]

        if not lists:
            raise InfoException(
                "购买人",
                "暂无购买人信息, 请到会员购平台绑定后再次使用!",
            )

        dist = []
        for info in lists:
            # 补充/删除信息
            info.pop("error_code")
            info["buyer"] = None
            info["disabledErr"] = None
            info["isBuyerInfoVerified"] = True
            info["isBuyerValid"] = True

            buyer_name = info["name"]
            buyer_id = info["personal_id"]
            buyer_tel = info["tel"]

            dist.append(
                {
                    "购买人": buyer_name[0] + "*" * 1 + buyer_name[-1],
                    "身份证": buyer_id[:6] + "*" * 8 + buyer_id[-4:],
                    "手机号": buyer_tel[:3] + "*" * 4 + buyer_tel[-4:],
                    "数据": info,
                }
            )
        return dist

    def Deliver(self) -> list:
        """
        收货地址

        接口: GET https://show.bilibili.com/api/ticket/addr/list
        """
        res = self.net.Response(
            method="get",
            url="https://show.bilibili.com/api/ticket/addr/list",
        )

        lists = res["data"]["addr_list"]

        if not lists:
            raise InfoException(
                "收货地址",
                "暂无收货地址信息, 请到会员购平台绑定后再次使用!",
            )

        dist = []
        for info in lists:
            dist.append(
                {
                    "name": info["name"],
                    "phone": info["phone"],
                    "addr": info["prov"] + info["city"] + info["area"] + info["addr"],
                    "info": {
                        "name": info["name"],
                        "tel": info["phone"],
                        "addr_id": info["id"],
                        "addr": info["prov"] + info["city"] + info["area"] + info["addr"],
                    },
                }
            )
        return dist

    def Userinfo(self) -> dict:
        """
        UID Username

        接口: GET https://api.bilibili.com/x/space/myinfo
        """
        res = self.net.Response(
            method="get",
            url="https://api.bilibili.com/x/space/myinfo",
        )

        dist = {
            "uid": res["data"]["mid"],
            "username": res["data"]["name"],
        }
        return dist
