import pandas

def convert(df: pandas.DataFrame):
    """
    メッシュ気候値用の変換関数。

    Args:
        df (DataFrame):
            変換処理をするデータフレーム。
    """
    names = ["G02_{0:03}".format(i) for i in range(2, 54)]
    names.extend(["G02_{0:03}".format(i) for i in range(59, 85)])
    for i in names:
        df[i] = df[i] / 10
    return df
