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
        self.saleFlagMap = {
            1: "不可售",
            2: "预售中",
            3: "已停售",
            4: "已售罄",
            5: "不可用",
            6: "库存紧张",
            8: "暂时售罄",
            9: "不在白名单",
            101: "未开始",
            102: "已结束",
            103: "未完成",
            105: "已下架",
            106: "已取消",
        }

    def QueryTicketProject(self, projectId: int) -> tuple[int, str, dict]:
        """
        项目基本信息

        projectId: 项目ID
        """
        url = "https://show.bilibili.com/api/ticket/project/getV2"
        params = {
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
                    "need_contact": not res["data"]["need_contact"],
                }
            case _:
                dist = {}

        return code, msg, dist

    def QueryGoodsProject(self, projectId: int) -> tuple[int, str, list[dict]]:
        """
        商品信息列表
        
        projectId: 项目ID
        """
        url = "https://show.bilibili.com/api/ticket/linkgoods/list"
        params = {
            "project_id": projectId,
            "page_type": "0",
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]

        match code:
            # 成功
            case 0:
                goods = res["data"]["list"]
                if not goods:
                    return code, msg, []

                dist = []
                for good in goods:
                    dist.append(
                        {
                            "link_id": good["id"],
                            "item_id": good["item_id"],
                            "name": good["detail"]["name"],
                            "display_name": good["sale_flag_txt"],
                            "sale_flag": good["sale_flag"],
                        }
                    )
            case _:
                dist = []

        return code, msg, dist

    def QueryTicketScreen(self, projectId: int) -> tuple[int, str, list[dict]]:
        """
        场次信息列表

        projectId: 项目ID
        """
        url = "https://show.bilibili.com/api/ticket/project/getV2"
        params = {
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
                data = res["data"]
                screens = data["screen_list"]

                if not screens:
                    raise InfoException("活动详情", "该活动暂未开放票务信息")

                dist = []
                for screen in screens:
                    dist.append(
                        {
                            "project_id": data["id"],
                            "id": screen["id"],
                            "name": screen["name"],
                            "sale_start": screen["sale_start"],
                            "sale_end": screen["sale_end"],
                            "express_fee": screen["express_fee"],
                            "salenum": screen["sale_flag_number"],
                            "saleflag": screen["saleFlag"]["display_name"],
                        }
                    )
            case _:
                dist = []

        return code, msg, dist

    def QueryTicketSku(self, projectId: int, screenId: int) -> tuple[int, str, list[dict]]:
        """
        票种信息列表

        screenId: 场次ID
        """
        url = "https://show.bilibili.com/api/ticket/project/getV2"
        params = {
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
                            "price": sku["price"],
                            "display_price": f"{(sku['price'] / 100):.2f}",
                            "sale_start": sku["saleStart"],
                            "sale_end": sku["saleEnd"],
                            "clickable": sku["clickable"],
                            "salenum": sku["sale_flag_number"],
                            "saleflag": sku["sale_flag"]["display_name"],
                            "num": sku["num"],
                            "act": {
                                "act_id": sku["discount_act"]["act_id"],
                                "act_type": sku["discount_act"]["act_type"],
                            } if sku["discount_act"] else {},
                        }
                    )
            case _:
                dist = []

        return code, msg, dist

    def QueryGoodsScreen(self, linkId: int) -> tuple[int, str, list[dict]]:
        """
        商品规格信息列表
        """
        url = "https://show.bilibili.com/api/ticket/linkgoods/detail"
        params = {
            "link_id": linkId,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]
        
        match code:
            # 成功
            case 0:
                screens = res["data"]["specs_list"]
                if not screens:
                    raise InfoException("商品详情", "该商品暂未开放票务信息")

                dist = []
                for screen in screens:
                    dist.append(
                        {
                            "id": screen["id"],
                            "name": screen["name"],
                            "display_name": self.sale_flag_map[screen["sale_flag_number"]],
                            "sale_start": screen["sale_start"],
                            "sale_end": screen["sale_end"],
                            "express_fee": screen["express_fee"],
                        }        
                    )
            case _:
                dist = []

        return code, msg, dist

    def QueryGoodsSku(self, linkId: int, specId: int) -> tuple[int, str, list[dict]]:
        """
        商品票种信息列表

        goodsId: 商品ID
        """
        url = "https://show.bilibili.com/api/ticket/linkgoods/detail"
        params = {
            "link_id": linkId,
        }
        res = self.net.Response(method="get", url=url, params=params)
        code = res["errno"]
        msg = res["msg"]
        
        match code:
            # 成功
            case 0:
                goods = res["data"]
                
                for i in res["data"]["specs_list"]:
                    if i["id"] == specId:
                        spec = i
                        skus = i["ticket_list"]
                        break

                dist = []
                for sku in skus:
                    dist.append(
                        {
                            "id": sku["id"],
                            "name": f"{goods['name']} - {spec['name']} - {sku['desc']}",
                            "display_name": self.saleFlagMap[sku["sale_flag_number"]],
                            "price": sku["price"],
                            "display_price": f"{(sku['price'] / 100):.2f}",
                            "sale_start": spec["sale_start"],
                            "sale_end": spec["sale_end"],
                            "clickable": sku["clickable"],
                            "salenum": sku["sale_flag_number"],
                            "num": sku["num"],
                            "act": {},
                        }
                    )
            case _:
                dist = []

        return code, msg, dist

    def Screen(self, projectId: int, screenId: int) -> tuple[int, str, dict]:
        """
        场次信息

        projectId: 项目ID
        screenId: 场次ID
        """
        code, msg, screens = self.QueryTicketScreen(projectId=projectId)

        for screen in screens:
            if screen["id"] == screenId:
                return code, msg, screen

        raise InfoException("场次查询", "指定场次不存在")

    def Sku(self, projectId: int, screenId: int, skuId: int, cost: int) -> tuple[int, str, dict]:
        """
        票种信息

        projectId: 项目ID
        screenId: 场次ID
        skuId: 票档ID
        cost: 价格
        """
        code, msg, skus = self.QueryTicketSku(projectId=projectId, screenId=screenId)

        for sku in skus:
            if sku["id"] == skuId and sku["price"] == cost:
                return code, msg, sku

        raise InfoException("场次查询", "指定票种不存在")

    def Buyer(self) -> list:
        """
        购买人

        接口: GET https://show.bilibili.com/api/ticket/buyer/list?is_default&projectId=${projectId}
        """
        url = "https://show.bilibili.com/api/ticket/buyer/list"
        res = self.net.Response(method="get", url=url)

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
        """
        url = "https://show.bilibili.com/api/ticket/addr/list"
        res = self.net.Response(method="get", url=url)

        lists = res["data"]["addr_list"]

        if not lists:
            raise InfoException("收货地址", "暂无收货地址信息, 请到会员购平台绑定后再次使用!")

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
        用户信息
        """
        url = "https://api.bilibili.com/x/space/myinfo"
        res = self.net.Response(method="get", url=url)

        dist = {
            "uid": res["data"]["mid"],
            "username": res["data"]["name"],
        }
        return dist

    def District(self) -> dict:
        """
        地区
        """
        url = "https://show.bilibili.com/api/ticket/district/geocoder"
        res = self.net.Response(method="get", url=url)

        dist = {
            "adcode": res["data"]["adcode"],
            "country": res["data"]["country"],
            "province": res["data"]["province"],
        }
        return dist

    def SearchList(self, keyword: str, page: int = 1) -> list[dict]:
        """
        搜索
        """
        url = "https://show.bilibili.com/api/ticket/search/list"
        params = {
            "version": "134",
            "platform": "web",
            "keyword": keyword,
            "pagesize": "20",
            "page": page,
        }
        res = self.net.Response(method="get", url=url, params=params)

        dist = []
        for project in res["data"]["result"]:
            dist.append(
                {
                    # "id": project["id"],
                    "project_name": project["project_name"],
                    # "sale_start": project["sale_start"],
                    "sale_flag": project["sale_flag"],
                    "countdown_flag": project["countdown"],
                }
            )
        return dist
