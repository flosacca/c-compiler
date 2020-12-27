from typing import TypeVar, Generic

T = TypeVar('T')


class Result(Generic[T]):

    def __init__(self, success: bool, value: T = None, message: str = None):
        self.success = success
        self.value = value
        self.message = message


def success_result(value: Generic[T]) -> Result[T]:
    return Result[T](True, value=value, message=None)


def failure_result(message: str) -> Result[T]:
    return Result[T](False, value=None, message=message)
