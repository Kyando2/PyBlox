import json
import time

from .Errors import *
from .Base import BloxType
from .User import BloxUser
from .Ranks import BloxRank
from .Settings import BloxSettings
from .Member import BloxMember
from .utils import Url, read_pages


class BloxGroup(BloxType):
    """
    A handler for a roblox group

    Attrs:
        `id`
        `roles`

    Fetchables:
        `join_requests`
        `name`
        `members`

    Meths:
        async `fetch`:
            >> name = await group.fetch("name") # where `group` is a BloxGroup

    Fetched users *will* be added to cache when using async meth `fetch`
    Attr `roles` will be deprecated in 1.1 in favor of Fetchable `roles`
    """
    def __init__(self, client, group_id, roles):
        super().__init__(client)
        self.id = str(group_id)
        self.roles = roles
        self.can_fetch("join_requests", "members", "name", "settings")

    def __str__(self):
        if self.name:
            return self.name
        raise AttributeNotFetched("name")
    
    async def fetch_name(self):
        hook = await Url("groups", "/v1/groups/%id%", id=self.id).get()

        name = hook.json.get("name", None)
        
        if name == None:
            raise PyBloxException(
                "Group name was not found"
                )

        return name

    # TODO: find a better way to do this (see BloxRank)
    async def _cvrt_dict_blox_member(self, list):
        real_list = []
        for user_dict in list:
            real_list.append(BloxMember(client=self.client, user_id=str(user_dict.get("userId")), username=user_dict.get("username"), group=self))

        return real_list

    async def get_role(self, name: str):
        """
        Returns a BloxRank with the given name
        """
        hook = await Url("groups", "/v1/groups/%id%/roles", id=self.id).get()
        
        data = hook.json
        roles = data.get("roles")

        for bucket in roles:
            if bucket.get("name") == name:
                return BloxRank(payload=bucket, group=self)

    async def get_member(self, username: str):
        user = await self.client.get_user(username)
        return BloxMember(client=self.client, user_id=user.id, username=username, group=self)

    async def fetch_members(self):
        """
        Returns a list of all the group's members
        """

        access = Url("groups", "/v1/groups/%id%/users?sortOrder=Asc&limit=100", id=self.id)

        def create_members(raw_data):
            return [BloxMember(client=self.client, user_id=str(user_dict.get("userId")), username=user_dict.get("username"), group=self) for user_dict in raw_data.get("data")]

        list_members = await read_pages(access, create_members)
        
        return list_members

    async def fetch_join_requests(self):
        """
        Returns a list of users that request to join the group

        Fetches settings
        """
        await self.fetch("settings")

        if not self.settings.is_approval_required:
            raise PyBloxException(
                "This group isn't approval required and has no join requests"
                )

        access = Url("groups", "/v1/groups/%id%/join-requests?sortOrder=Asc&limit=100", id=self.id)

        def create_users(raw_data):
            return [BloxUser(client=self.client, user_id=str(user_dict['user'].get("userId")), username=user_dict['user'].get("username")) for user_dict in raw_data.get("data")]

        list_members = await read_pages(access, create_users)

        return list_members

    async def fetch_settings(self):
        """
        Returns a `BloxSetting` object
        """
        access = Url("groups", "/v1/groups/%id%/settings", id=self.id)
        data = await access.get()
        data = data.json

        return BloxSettings(payload=data)
        
