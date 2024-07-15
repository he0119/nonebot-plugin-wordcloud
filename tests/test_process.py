def process_messages():
    from nonebot_plugin_wordcloud.data_source import analyse_messages

    msgs = [
        "这是一个奇怪的句子。",
        "1😅🟨二",
        "1👨🏿‍🔧👨‍👨‍👧‍👧🛀🏽🧑🏽‍❤️‍🧑🏾1",
        "1  2",
        "1 http://v2.nonebot.dev/ 2",
        "1 https://v2.nonebot.dev/ 2",
        "1 https://api.weibo.cn/share/312975272,47087.html?weibo_id=4770873388 2",
    ]
    frequencies = analyse_messages(msgs)

    # You may return anything you want, like the result of a computation
    return frequencies


def test_process_messages(benchmark, snapshot):
    frequencies = benchmark(process_messages)

    assert frequencies == snapshot
