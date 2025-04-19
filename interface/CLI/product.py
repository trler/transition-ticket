import re
import sys
from time import sleep

from loguru import logger

from util import Config, Data, Info, Request
from util.Info import InfoException


class ProductCli:
    """
    商品配置交互
    """

    @logger.catch
    def __init__(self, conf: Config):
        """
        初始化

        conf: 配置实例
        """
        self.conf = conf

        self.data = Data()
        self.net = Request()
        self.info = Info(net=self.net)

        # 配置
        self.config = {
            # 活动ID
            "projectId": 0,
            # 场次ID
            "screenId": 0,
            # 票种ID
            "skuId": 0,
            # 票价
            "cost": 0,
            # 优惠信息
            "act": {},
        }

        # 颜色ANSI代码
        self.YELLOW = "\033[93m"
        self.BLUE = "\033[96m"
        self.RESET = "\033[0m"

    @logger.catch
    def Select(self, selects: list) -> dict:
        """
        选择配置

        selects: 可选择项目
        """
        if selects[-1] != "新建商品配置":
            selects.append("新建商品配置")

        select = self.data.Inquire(
            type="List",
            message="请选择加载的商品配置",
            choices=selects,
        )

        if select == "新建商品配置":
            return self.Generate()

        else:
            self.config = self.conf.Load(filename=select)
            return self.config

    @logger.catch
    def Generate(self) -> dict:
        """
        生成配置
        """

        @logger.catch
        def ProjectStep() -> tuple[int, int]:
            """
            活动
            
            活动：https://show.bilibili.com/platform/detail.html?id=114514
            商品：https://mall.bilibili.com/neul-next/detailuniversal/detail.html?itemsId=12092996
            """
            # print(f"{self.BLUE}[{self.YELLOW}!{self.BLUE}]{self.RESET} 近期活动: show.bilibili.com/platform/detail.html?id=114514")
            url = self.data.Inquire(
                type="Text",
                message="请粘贴要抢的活动的网页链接",
            )

            try:
                match_show = re.search(r"id=(\d+)", url)
                match_mall = re.search(r"itemsId=(\d+)", url)
                if match_show:
                    projectId = int(match_show.group(1))
                    return 1, projectId
                elif match_mall:
                    projectId = int(match_mall.group(1))
                    return 2, projectId
                else:
                    raise InfoException("商品配置初始化", "商品URL格式错误!")

            except InfoException:
                logger.warning("请重新配置活动信息!")
                return ProjectStep()

        @logger.catch
        def GoodsStep(projectId: int) -> int:
            """
            商品
            
            projectId: 活动ID
            """
            try:
                _, _, projectInfo = self.info.QueryProject(projectId=projectId)
                _, _, goodsInfo = self.info.QueryGoods(projectId=projectId)

                if not goodsInfo:
                    return 0

                lists = {
                    f"{self.YELLOW if i['display_name'] == '预售中' else ''}"
                    f"{i['name']} ({i['display_name']})"
                    f"{self.RESET if i['display_name'] == '预售中' else ''}": i["link_id"]
                    for i in goodsInfo
                }
                select = self.data.Inquire(
                    type="List",
                    message=f"您选择的活动是:{projectInfo['name']}, 接下来请选择商品",
                    choices=list(lists.keys()),
                )
                return lists[select]

            except InfoException:
                logger.exception("请重新配置活动信息!")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

        @logger.catch
        def ScreenStep(projectId: int, linkId: int) -> int:
            """
            场次
            """
            try:
                _, _, projectInfo = self.info.QueryTicketProject(projectId=projectId)
                _, _, screenInfo = self.info.QueryTicketScreen(projectId=projectId)
                
                if linkId:
                    _, _, specInfo = self.info.QueryGoodsSpec(linkId=linkId)
                    screenInfo = screenInfo + specInfo

                lists = {
                    f"{self.YELLOW if screen['saleflag'] == '预售中' else ''}"
                    f"{screen['name']} ({screen['saleflag']})"
                    f"{self.RESET if screen['saleflag'] == '预售中' else ''}": screen
                    for screen in screenInfo
                }
                select = self.data.Inquire(
                    type="List",
                    message=f"您选择的活动是:{projectInfo['name']}, 接下来请选择场次",
                    choices=list(lists.keys()),
                )
                return (
                    lists[select]["id"],
                    lists[select]["express_fee"],
                    projectInfo["name"],
                    projectInfo["need_deliver"],
                    projectInfo["need_contact"],
                )

            except InfoException:
                logger.exception("请重新配置活动信息!")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

        @logger.catch
        def SkuStep(projectId: int, linkId: int, screenId: int) -> tuple:
            """
            价位

            screenId: 场次ID
            """
            try:

                if linkId:
                    _, _, skuInfo = self.info.QueryGoodsSku(linkId=linkId, specId=screenId)
                else:
                    _, _, skuInfo = self.info.QueryTicketSku(projectId=projectId, screenId=screenId)
                    
                
                lists = {
                    f"{self.YELLOW if sku['saleflag'] == '预售中' else ''}"
                    f"{sku['name']} {sku['display_price']}元 ({sku['saleflag']})"
                    f"{self.RESET if sku['saleflag'] == '预售中' else ''}": sku
                    for sku in skuInfo
                }
                select = self.data.Inquire(
                    type="List",
                    message="请选择价位",
                    choices=list(lists.keys()),
                )
                return (
                    lists[select]["id"],
                    lists[select]["name"] + " " + lists[select]["display_price"],
                    lists[select]["sale_start"],
                    lists[select]["price"],
                    lists[select]["act"],
                )

            except InfoException:
                logger.exception("请重新配置活动信息!")
                logger.warning("程序正在准备退出...")
                sleep(5)
                sys.exit()

        @logger.catch
        def FilenameStep(name: str) -> str:
            """
            文件名

            skuid: 价位ID
            """
            filename = self.data.Inquire(
                type="Text",
                message="保存的商品文件名称",
                default=name,
            )
            return filename

        print("下面开始配置商品!")

        projectId = ProjectStep()
        screenId, expressFee, projectName, needDeliver, needContact = ScreenStep(projectId=projectId)
        skuId, skuSelected, saleStart, cost, act = SkuStep(projectId=projectId, screenId=screenId)

        self.config["projectId"] = projectId
        self.config["screenId"] = screenId
        self.config["skuId"] = skuId
        self.config["saleStart"] = saleStart
        self.config["cost"] = cost
        self.config["deliverFee"] = max(expressFee, 0)
        self.config["act"] = act
        self.config["needDeliver"] = needDeliver
        self.config["needContact"] = needContact

        self.conf.Save(
            FilenameStep(name=f"{projectName} ({skuSelected})"),
            self.config,
        )
        logger.info("【商品配置初始化】配置已保存!")
        return self.config
