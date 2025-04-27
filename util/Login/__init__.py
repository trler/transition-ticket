import json
import re
import sys
import time
from time import sleep

from loguru import logger
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from util.Captcha import Captcha
from util.Data import Data
from util.Request import Request


class LoginException(Exception):
    """
    登录异常
    """

    def __init__(self, message):
        self.message = message
        logger.error(f"【登录】{message}")


class Login:
    """
    账号登录

    文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action
    """

    @logger.catch
    def __init__(self, net=Request, isCheckStatus: bool = True):
        """
        初始化

        net: 网络实例
        isCheckStatus: 是否检查登录状态
        """
        self.net = net
        self.isCheckStatus = isCheckStatus

        self.data = Data()
        self.cap = Captcha()

        self.cookie = {}
        self.source = "main_h5"

    @logger.catch
    def __GetCaptcha(self) -> tuple:
        """
        获取Captcha验证码并通过Geetest验证

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/readme.md
        """
        res = self.net.Response(
            method="get",
            url="https://passport.bilibili.com/x/passport-login/captcha?source=main_web",
        )

        if res["code"] == 0:
            token = res["data"]["token"]
            challenge = res["data"]["geetest"]["challenge"]
            validate = self.cap.Geetest(challenge)
            seccode = validate + "|jordan"
            return token, challenge, validate, seccode
        else:
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

    @logger.catch
    def __GetPreCaptcha(self) -> tuple:
        """
        获取PreCaptcha验证码并通过Geetest验证

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/readme.md
        """
        res = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/safecenter/captcha/pre",
            isJson=False,
        )

        if res["code"] == 0:
            token = res["data"]["recaptcha_token"]
            challenge = res["data"]["gee_challenge"]
            validate = self.cap.Geetest(challenge)
            seccode = validate + "|jordan"
            return token, challenge, validate, seccode
        else:
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

    def QRCode(self) -> dict:
        """
        扫码登录

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/QR.md
        """
        res = self.net.Response(
            method="get",
            url="https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
            isJson=False,
        )

        if res["code"] != 0:
            raise LoginException(f"服务器不知道送来啥东西{json.dumps(res, indent=4)}")

        _url = res["data"]["url"]
        self.data.QRGenerate(_url)

        t = 0
        while True:
            time.sleep(0.5)
            _res = self.net.Response(
                method="get",
                url="https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
                params={
                    "qrcode_key": res["data"]["qrcode_key"],
                },
            )

            match _res["data"]["code"]:
                case 0:
                    logger.success("【登录】登录成功")
                    self.cookie = self.net.GetCookie()
                    return self.Status()

                # 未扫描: 86101 扫描未确认: 86090
                case 86101 | 86090:
                    t += 1
                    if t % 5 == 0:
                        logger.info("【登录】等待扫码...")

                case _:
                    raise LoginException(f"{_res['data']['code']}: {_res['data']['message']}")

    def Selenium(self) -> dict:
        """
        Selenium登录
        """
        print("请在打开的浏览器中进行登录")
        driver = webdriver.Edge()

        if not driver:
            raise LoginException("浏览器尝试启动失败")

        driver.maximize_window()
        try:
            driver.get("https://show.bilibili.com/")
            wait = WebDriverWait(driver, 30)
            event = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "nav-header-register")))
            driver.execute_script("arguments[0].click();", event)

        except Exception:
            logger.warning("程序正在准备退出...")
            sleep(5)
            sys.exit()

        while True:
            time.sleep(0.5)
            if driver.page_source is None or "登录" not in driver.page_source:
                break

        logger.success("【登录】登录成功")
        driver.get("https://account.bilibili.com/account/home")
        seleniumCookie = driver.get_cookies()
        logger.info("【登录】Cookie已保存")
        self.cookie = self.data.SeleniumCookieFormat(seleniumCookie)
        driver.quit()
        return self.Status()

    def Password(self, username: str, password: str) -> dict:
        """
        账号密码登录

        username: 用户名
        password: 密码

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/password.md
        """
        token, challenge, validate, seccode = self.__GetCaptcha()

        salt = self.net.Response(
            method="get",
            url="https://passport.bilibili.com/x/passport-login/web/key",
            isJson=False,
        )

        salt_hash = salt["data"]["hash"]
        salt_key = salt["data"]["key"]

        res = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/passport-login/web/login",
            params={
                "username": username,
                "password": self.data.PasswordRSAEncrypt(salt_hash + password, salt_key),
                "keep": "0",
                "token": token,
                "challenge": challenge,
                "validate": validate,
                "seccode": seccode,
                "source": self.source,
            },
            isJson=False,
        )

        if res["code"] != 0:
            raise LoginException(f"登录失败 {res['code']}: {res['message']}")

        _status = res["data"]["status"]
        if _status == 0:
            logger.success("【登录】登录成功")
            self.cookie = self.net.GetCookie()
            return self.Status()

        else:
            logger.warning("【登录】登录失败, 需要二次验证")

            _url = res["data"]["url"]
            _match_token = re.search(r"tmp_token=(\w{32})", _url)
            _token = _match_token.group(1) if _match_token else ""
            _match_scene = re.search(r"scene=([^&]+)", _url)
            _scene = _match_scene.group(1) if _match_scene else "loginTelCheck"

            res_info = self.net.Response(
                method="get",
                url="https://passport.bilibili.com/x/safecenter/user/info",
                params={
                    "tmp_code": _token,
                },
                isJson=False,
            )

            if not res_info["data"]["account_info"]["bind_tel"]:
                raise LoginException("手机号未绑定, 请重新选择登录方式")

            hide_tel = res_info["data"]["account_info"]["hide_tel"]
            logger.info(f"【登录】手机号已绑定, 即将给 {hide_tel} 发送验证码")

            token, challenge, validate, seccode = self.__GetPreCaptcha()

            res_resend = self.net.Response(
                method="post",
                url="https://passport.bilibili.com/x/safecenter/common/sms/send",
                params={
                    "tmp_code": _token,
                    "sms_type": _scene,
                    "recaptcha_token": token,
                    "gee_challenge": challenge,
                    "gee_validate": validate,
                    "gee_seccode": seccode,
                },
                isJson=False,
            )

            if res_resend["code"] != 0:
                raise LoginException(f"验证码发送失败: {res_resend['code']} {res_resend['message']}")

            logger.success("【登录】验证码发送成功")
            token = res_resend["data"]["captcha_key"]
            verify_code = self.data.Inquire(type="Text", message="请输入验证码")

            if _status == 1:
                params = {
                    "verify_type": "sms",
                    "tmp_code": _token,
                    "captcha_key": token,
                    "code": verify_code,
                }
                url = "https://passport.bilibili.com/x/safecenter/sec/verify"

            elif _status == 2:
                params = {
                    "type": "loginTelCheck",
                    "tmp_code": _token,
                    "captcha_key": token,
                    "code": verify_code,
                }
                url = "https://passport.bilibili.com/x/safecenter/login/tel/verify"

            else:
                raise LoginException(f"未知错误: {res['data']['status']}")

            res_reverify = self.net.Response(method="post", url=url, params=params)

            if res_reverify["code"] != 0:
                raise LoginException(f"验证码登录失败 {res_reverify['code']}: {res_reverify['message']}")

            logger.success("【登录】验证码登录成功")
            self.net.Response(
                method="post",
                url="https://passport.bilibili.com/x/passport-login/web/exchange_cookie",
                params={
                    "source": "risk",
                    "code": res_reverify["data"]["code"],
                },
                isJson=False,
            )

            self.cookie = self.net.GetCookie()
            return self.Status()

    def SMSSend(self, tel: int) -> str:
        """
        手机号登录 - 发送验证码

        tel: 手机号
        返回: captcha_key

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/SMS.md
        """
        token, challenge, validate, seccode = self.__GetCaptcha()

        params = {
            "cid": 86,
            "tel": tel,
            "source": self.source,
            "token": token,
            "challenge": challenge,
            "validate": validate,
            "seccode": seccode,
        }

        res = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/passport-login/web/sms/send",
            params=params,
            isJson=False,
        )

        if res["code"] == 0:
            logger.success("【登录】验证码发送成功")
            captcha_key = res["data"]["captcha_key"]
            return captcha_key
        else:
            raise LoginException(f"验证码发送失败 {res['code']}: {res['message']}")

    def SMSVerify(self, tel: int, code: int, captcha_key: str) -> dict:
        """
        手机号登录 - 发送验证码

        tel: 手机号
        int: 验证码
        captcha_key: 验证token

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_action/SMS.md
        """
        params = {
            "cid": 86,
            "tel": tel,
            "code": code,
            "source": self.source,
            "captcha_key": captcha_key,
            "keep": False,
        }

        res = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/x/passport-login/web/login/sms",
            params=params,
            isJson=False,
        )

        if res["code"] == 0:
            logger.success("【登录】登录成功")
        else:
            raise LoginException(f"验证码登录失败 {res['code']}: {res['message']}")

        self.cookie = self.net.GetCookie()
        return self.Status()

    def Cookie(self, cookie: str) -> dict:
        """
        Cookie登录

        cookie: Cookie字符串
        """
        self.cookie = self.data.StrCookieFormat(cookie)
        return self.Status()

    def Status(self) -> dict:
        """
        登录状态

        文档: https://github.com/SocialSisterYi/bilibili-API-collect/blob/master/docs/login/login_info.md
        """
        self.net.RefreshCookie(self.cookie)

        if self.isCheckStatus:
            user = self.net.Response(
                method="get",
                url="https://api.bilibili.com/x/web-interface/nav",
            )

            if user["data"]["isLogin"]:
                return self.cookie
            else:
                raise LoginException("登录状态检测失败")

        else:
            logger.info("【登录状态检测】已关闭")
            return self.cookie

    @logger.catch
    def ExitLogin(self) -> bool:
        """
        退出登录
        """
        res = self.net.Response(
            method="post",
            url="https://passport.bilibili.com/login/exit/v2",
            params={"biliCSRF": self.net.GetCookie()["bili_jct"]},
        )

        if res["code"] == 0:
            logger.info("【退出登录】注销Cookie成功")
            return True
        elif res["code"] == 2202:
            logger.error("【退出登录】CSRF请求非法")
            return False
        else:
            logger.error("【退出登录】发生了什么")
            return False
