import logging
import re

import aiohttp

from ..Response import BloxResponse
from ..Errors import HttpError


csrfTokenRegex = re.compile(r"Roblox.XsrfToken.setToken\('(.+)'\)")
logger = logging.getLogger(__name__)


ENDPOINTS = {
    "groups": "groups.roblox.com",
    "friends": "friends.roblox.com",
    "default": "api.roblox.com"
}

class HttpClient:
    __instance = None

    @staticmethod
    def get():
        return HttpClient.__instance

    def __init__(self, loop, headers: dict={}):
        self.__headers = headers
        self.__loop = loop
        self.__cookies = {}
        self.__authed = False
        HttpClient.__instance = self

    async def close(self):
        if self.__authed:
            await self.__session.close()

    async def connect(self, roblosecurity):
        '''
        Creates the connection header and verifies the connection
        '''
        self.__set_cookie(".ROBLOSECURITY", roblosecurity, None)
        self.__session = aiohttp.ClientSession(loop=self.__loop)
        await self.__actualize_token()
        user = await self.__complete_login(self.__headers.copy())

        self.__authed = True
        logger.info("Connection Established")
        return user

    async def __complete_login(self, headers):

        logger.info("Validating Auth")

        try:
            resp = await Url("www.roblox.com", "/my/settings/json").get()
        except HttpError as e:
            logger.critical("Login failed")
            raise

        resp = resp.json
        
        return [resp.get("UserId"), resp.get("Name")]

    async def __raw_request(self, method, url, data=None, headers=None) -> BloxResponse:
        logger.info("Requesting url {}".format(url))
        async with self.__session.request(method=method, url=url, data=data, headers=headers) as resp:
            text = await resp.text()
            return BloxResponse(status=resp.status, text=text, headers=resp.headers)

    async def request(self, method, url, data=None, headers=None, retries=0):
        if not headers:
            headers = self.__headers

        if method == "GET":
            headers["content-type"] = "application/json"

        response = await self.__raw_request(method, url, data, headers)

        if not response.status == 200:
            if not retries>0:
                await self.__actualize_token()
                await self.request(method, url, data, headers, retries=retries+1)
            HttpError.error(response.status)
        else:
            return response

    async def __actualize_token(self):
        response = await self.__raw_request(method='GET', url='https://www.roblox.com/')
            
        token = re.findall(
            csrfTokenRegex,
            response.text
        )

        if len(token) > 0:
            if self.__headers.get("X-CSRF-TOKEN", None) != token[0]:
                logger.info(" Updated X-CSRF-TOKEN " + token[0] + " <")
                self.__set_header("X-CSRF-TOKEN", token[0])

    # Helper
    def __set_header(self, key, value):
        self.__headers[key] = value

    # Helper
    def __set_cookie(self, key, value, cookieProps):
        self.__cookies[key] = value

        cookie_list = []
        for k,v in self.__cookies.items():
            cookie_list.append(k)
            cookie_list.append("=")
            cookie_list.append(v)
            cookie_list.append(";")

        self.__set_header("Cookie", "".join(cookie_list))


class Url:

    def __init__(self, endpoint: str, url: str, **params):
        endpoint = ENDPOINTS.get(str.lower(endpoint), endpoint)
        self.__http = HttpClient.get()
        if params:
            for k, v in params.items():
                url = url.replace('%'+k+'%', str(v), 1)
        url = endpoint + url
        self.__url = "https://" + url

    @property
    def url(self):
        return self.__url

    ''' HTTP methods '''
    async def get(self, data=None, headers=None):
        return await self.__http.request("GET", self.__url, data, headers)

    async def post(self, data=None, headers=None):
        return await self.__http.request("POST", self.__url, data, headers)

    async def put(self, data=None, headers=None):
        return await self.__http.request("PUT", self.__url, data, headers)

    async def delete(self, data=None, headers=None):
        return await self.__http.request("DELETE", self.__url, data, headers)

    async def patch(self, data=None, headers=None):
        return await self.__http.request("PATCH", self.__url, data, headers)
      

        