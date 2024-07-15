import abc
from collections.abc import Iterable
from functools import cache
from typing import Union


class Processor:
    @abc.abstractmethod
    @cache
    def process_msg(self, msg: str) -> Union[str, list[str]]:
        raise NotImplementedError

    def process_msgs(
        self, msgs: Iterable[str]
    ) -> Union[Iterable[str], dict[str, float]]:
        new_msgs = []
        for msg in msgs:
            processed_msg = self.process_msg(msg)
            if isinstance(processed_msg, str):
                new_msgs.append(processed_msg)
            else:
                new_msgs.extend(processed_msg)
        return new_msgs
