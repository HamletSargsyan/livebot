from aiogram.enums import ChatType
from aiogram.filters import BaseFilter
from aiogram.types import Message


class IsDigitFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.text.isdigit()


class ChatTypeFilter(BaseFilter):
    def __init__(self, *chat_types: ChatType):
        self.chat_types = chat_types

    async def __call__(self, message: Message) -> bool:
        return any(message.chat.type == chat_type for chat_type in self.chat_types)
