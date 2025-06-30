import logging
from time import sleep

import httpx
from fake_useragent import UserAgent
from loguru import logger


class Request:
    """
    网络请求
    """

    @logger.catch
    def __init__(
        self,
        cookie: dict = {},
        header: dict = {},
        timeout: float = 5.0,
        proxy: str | None = None,
        redirect: bool = True,
        isDebug: bool = False,
        rest: float = 60.0,
    ):
        """
        初始化

        cookie: Dict Cookie
        timeout: 超时
        proxy: 代理
        redirect: 重定向
        isDebug: 调试模式
        rest: 412风控间隔
        """

        self.cookie = cookie
        self.timeout = timeout
        self.proxy = proxy
        self.redirect = redirect
        self.isDebug = isDebug
        self.rest = rest

        self.header = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            "Connection": "keep-alive",
            "User-Agent": UserAgent(os="Android", platforms="mobile").random,
        } | header

        self.session = httpx.Client(
            cookies=self.cookie,
            headers=self.header,
            timeout=self.timeout,
            proxy=self.proxy,
            # 重定向
            follow_redirects=self.redirect,
            # HTTP2
            http2=True,
            # SSL
            verify=False,
            # Hook
            event_hooks={
                "request": [self.RequestHook],
                "response": [self.ResponseHook],
            },
        )

        # 关闭Httpx自带日志
        logging.getLogger("httpx").setLevel(logging.CRITICAL)

    @logger.catch
    def Response(
        self,
        method: str,
        url: str,
        params: dict = {},
        isJson: bool = True,
        isRedirect: bool = True,
    ) -> dict:
        """
        网络

        method: 方法 post/get
        url: 地址
        params: 参数
        isJson: 请求是否为 application/json
        isRedirect: 是否允许重定向
        """
        methods = {
            "get": self.session.get,
            "post": self.session.post,
        }

        if method not in methods:
            logger.warning("? 这是什么方式")

        if 'ptoken' in params:
            query_params = [f"ptoken={params['ptoken']}"]
            if 'project_id' in params:
                query_params.append(f"project_id={params['project_id']}")
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}{'&'.join(query_params)}"


        try:
            if isJson:
                # self.session.headers.update({"Content-Type": "application/json"})
                dist: httpx.Response = methods[method](
                    url=url,
                    follow_redirects=isRedirect,
                    **({"params": params} if method == "get" else {"json": params}),
                )
            else:
                # self.session.headers.update({"Content-Type": "application/x-www-form-urlencoded"})
                dist: httpx.Response = methods[method](
                    url=url,
                    follow_redirects=isRedirect,
                    **({"params": params} if method == "get" else {"data": params}),
                )

            if dist.status_code == 200:
                if "application/json" in dict(dist.headers)["content-type"]:
                    res = dist.json()
                    code = res.get("errno") if res.get("errno") is not None else res.get("code")
                    msg = res.get("msg") if res.get("msg") is not None else res.get("message")
                    return {
                        "code": code,
                        "errno": code,
                        "msg": msg,
                        "message": msg,
                        **{k: v for k, v in res.items() if k not in ["code", "errno", "msg", "message"]},
                    }
                else:
                    return {
                        "code": 114514,
                        "errno": 114514,
                        "msg": f"请求错误: {dist.status_code}",
                        "message": f"请求错误: {dist.status_code}",
                    }
            elif dist.status_code in range(300, 400) and not isRedirect:
                return dist.headers.get("Location")
            else:
                return {
                    "code": 114514,
                    "errno": 114514,
                    "msg": f"请求错误: {dist.status_code}",
                    "message": f"请求错误: {dist.status_code}",
                }

        except (
            httpx.RequestError,
            httpx.HTTPStatusError,
            httpx.StreamError,
        ) as e:
            return {
                "code": 114514,
                "errno": 114514,
                "msg": f"请求错误: {e}",
                "message": f"请求错误: {e}",
            }

    @logger.catch
    def GetCookie(self) -> dict:
        """
        获取Cookie
        """
        return dict(self.session.cookies)

    @logger.catch
    def GetHeader(self) -> dict:
        """
        获取Header
        """
        return dict(self.session.headers)

    @logger.catch
    def RefreshCookie(self, cookie: dict) -> None:
        """
        刷新Cookie

        cookie: Cookie
        """
        self.cookie = cookie
        self.session.cookies.update(self.cookie)

    @logger.catch
    def RefreshHeader(self, header: dict) -> None:
        """
        刷新Header

        header: Header
        """
        self.header = header
        self.session.headers.update(self.header)

    @logger.catch
    def RequestHook(self, request: httpx.Request) -> None:
        """
        请求事件钩子
        """
        # 调试模式
        if self.isDebug:
            logger.debug(f"【Request请求】地址: {request.url} 方法: {request.method} 内容: {request.content} 请求参数: {request.read()}")

    @logger.catch
    def ResponseHook(self, response: httpx.Response) -> None:
        """
        响应事件钩子
        """
        request = response.request
        # 调试模式
        if self.isDebug:
            logger.debug(f"【Request响应】地址: {request.url} 状态码: {response.status_code} 返回: {response.read()}")

        # 错误
        if response.status_code != 200:
            if response.status_code == 412:
                logger.error(
                    f"【Request响应】IP被B站封禁(412风控)!!!!! 下面暂停工作{self.rest}秒, 请更换IP后再次使用(重启路由器/使用手机流量热点/代理...)"
                )
                sleep(self.rest)

            # 等于100001
            elif response.status_code == 429 or "show.bilibili.com" not in str(request.url):
                pass

            else:
                logger.error(f"【Request响应】请求错误, 状态码: {response.status_code}")
