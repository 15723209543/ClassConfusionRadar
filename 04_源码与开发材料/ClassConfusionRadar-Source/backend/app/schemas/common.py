"""
本文件的作用是：定义common接口使用的数据结构与校验规则。
"""
from pydantic import BaseModel


class ApiMessage(BaseModel):
    message: str
