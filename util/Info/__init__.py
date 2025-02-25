from loguru import logger

from util import Request


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

    def Project(self, projectId: int) -> dict:
        """
        项目基本信息

        projectId: 项目ID
        """
        res = self.net.Response(
            method="get",
            url=f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={projectId}",
        )

        base_info_id = 0
        for i, item in enumerate(res["data"]["performance_desc"]["list"]):
            if item["module"] == "base_info":
                base_info_id = i
                break

        dist = {
            "id": res["data"]["id"],
            "name": res["data"]["name"],
            "time": res["data"]["performance_desc"]["list"][base_info_id]["details"][0]["content"],
            "need_deliver": res["data"]["has_paper_ticket"],
            "need_contact": res["data"]["need_contact"],
        }
        return dist

    def ScreenList(self, projectId: int) -> list[dict]:
        """
        场次信息列表

        projectId: 项目ID
        """
        res = self.net.Response(
            method="get",
            url=f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={projectId}",
        )

        screens = res["data"]["screen_list"]
        if not screens:
            raise InfoException("活动详情", "该活动暂未开放票务信息")

        dist = []
        for screen in screens:
            dist.append({
                "id": screen["id"],
                "name": screen["name"],
                "display_name": screen["saleFlag"]["display_name"],
                "sale_start": screen["sale_start"],
                "sale_end": screen["sale_end"],
                "express_fee": screen["express_fee"],
                # "express_free_flag": screen["express_free_flag"],
            })
        return dist

    def Screen(self, projectId: int, screenId: int) -> dict:
        """
        场次信息

        projectId: 项目ID
        screenId: 场次ID
        """
        screens = self.ScreenList(projectId=projectId)

        for screen in screens:
            if screen["id"] == screenId:
                return screen
        raise InfoException("场次查询", "指定场次不存在")

    def SkuList(self, projectId: int, screenId: int) -> list[dict]:
        """
        票种信息列表

        screenId: 场次ID
        """
        res = self.net.Response(
            method="get",
            url=f"https://show.bilibili.com/api/ticket/project/getV2?version=134&id={projectId}",
        )

        for i in res["data"]["screen_list"]:
            if i["id"] == screenId:
                skus = i["ticket_list"]
                break

        dist = []
        for sku in skus:
            dist.append({
                "id": sku["id"],
                "name": f"{sku['screen_name']} - {sku['desc']}",
                "display_name": sku["sale_flag"]["display_name"],
                "price": sku["price"],
                "display_price": f"{(sku['price'] / 100):.2f}",
                "sale_start": sku["saleStart"],
                "sale_end": sku["saleEnd"],
                "act": {
                    "act_id": sku["discount_act"]["act_id"],
                    "act_type": sku["discount_act"]["act_type"],
                }
                if sku["discount_act"] else {},
            })
        return dist

    def Sku(self, projectId: int, screenId: int, skuId: int, cost: int) -> dict:
        """
        票种信息

        projectId: 项目ID
        screenId: 场次ID
        skuId: 票档ID
        cost: 价格
        """
        skus = self.SkuList(projectId=projectId, screenId=screenId)

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
            raise InfoException("购买人", "暂无购买人信息, 请到会员购平台绑定后再次使用!")

        buyers_info = []
        for _i, info in enumerate(lists):
            # 补充/删除信息
            info.pop("error_code")
            info["buyer"] = None
            info["disabledErr"] = None
            info["isBuyerInfoVerified"] = True
            info["isBuyerValid"] = True

            buyer_name = info["name"]
            buyer_id = info["personal_id"]
            buyer_tel = info["tel"]

            buyer_info = {
                "购买人": buyer_name[0] + "*" * 1 + buyer_name[-1],
                "身份证": buyer_id[:6] + "*" * 8 + buyer_id[-4:],
                "手机号": buyer_tel[:3] + "*" * 4 + buyer_tel[-4:],
                "数据": info,
            }
            buyers_info.append(buyer_info)
        return buyers_info

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
            raise InfoException("收货地址", "暂无收货地址信息, 请到会员购平台绑定后再次使用!")

        delivers_info = []
        data_info = {}
        for _i, info in enumerate(lists):
            data_info["name"] = info["name"]
            data_info["tel"] = info["phone"]
            data_info["addr_id"] = info["id"]
            data_info["addr"] = info["prov"] + info["city"] + info["area"] + info["addr"]

            deliver_info = {
                "收货人": data_info["name"],
                "手机号": data_info["tel"],
                "地址": data_info["addr"],
                "数据": data_info,
            }
            delivers_info.append(deliver_info)
        return delivers_info

    def Userinfo(self) -> dict:
        """
        UID Username

        接口: GET https://api.bilibili.com/x/space/myinfo
        """
        res = self.net.Response(
            method="get",
            url="https://api.bilibili.com/x/space/myinfo",
        )

        userinfo = {
            "uid": res["data"]["mid"],
            "username": res["data"]["name"],
        }
        return userinfo
