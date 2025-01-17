from aiogram.types import Message
from aiogram.filters import BaseFilter


class IsDigitFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.text.isdigit()
