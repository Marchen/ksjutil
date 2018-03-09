"""
ksj: 国土数値情報を操作するパッケージ

現在のところ国土数値情報をきれいにするcleanup()関数が入っている。

Depends:
    os, typing, numpy, pandas

Suggests:
    geopandas


例：

import geopandas
import ksj

gpd = geopandas.read_file("文化施設/P27-13.shp")
clean_gpd = ksj.cleanup(gpd)
clean_gpd.head()

"""

#=============================================================================
#   準備
#=============================================================================

import os
from typing import Callable, Dict, Tuple

import numpy
import pandas

__all__ = ["cleanup"]


#=============================================================================
#   定数の読み込み
#=============================================================================
def _read_column_name_conversion() -> Tuple[Dict[str, str]]:
    """
    列名対応表を読み込む。

    Returns:
        dict, dict:
            {"国土数値情報列名コード": "列名"}型の辞書。
            １番目の辞書が日本語、２番目が英語。
            ただし、英語はまだほとんど実装していない。
    """
    path = os.path.join(
        os.path.dirname(__file__), "_data", "column_names.txt"
    )
    df = pandas.read_csv(path, encoding = "utf_8",  sep = "\t")
    conv_ja = {key: value for key, value in zip(df["対応番号"], df["属性名"])}
    conv_en = {key: value for key, value in zip(df["対応番号"], df["name"])}
    return (conv_ja, conv_en)

_COLUMNS_JA, _COLUMNS_EN = _read_column_name_conversion()


#=============================================================================
#   関数定義
#=============================================================================

#-----------------------------------------------------------------------------
def _read_codelist_file(column_name: str) -> (None, Dict[int, str]):
    """
    コードとデータの変換表を読み込む。

    「列名.txt」というフォーマットで_dataフォルダに保存されている
    対応表を探し、もし見つかったら列名を変換する。
    対応表はUTF-8のタブ区切りテキストで、
    コードの列名がcode、変換後のデータの列名がdataである必要がある。

    Args:
        column_name (str):
            変換するコードの列名。

    Returns:
        None, dict:
            変換表が見つかった場合、{code: data}形式の辞書を返す。
            codeは文字列ではなく整数型になるので、
            変換前にコードのデータ型を文字列から整数に変更しておく必要がある。
            変換表が見つからない場合、Noneを返す。

    """
    path = os.path.join(
        os.path.dirname(__file__), "_data", column_name + ".txt"
    )
    if not os.path.exists(path):
        return
    codelist = pandas.read_csv(path, sep = "\t", encoding = "utf_8")
    return {code: data for code, data in zip(codelist.code, codelist.data)}


#-----------------------------------------------------------------------------
def _create_read_code_list_fun() -> Callable:
    """
    キャッシュ機能付きの国土数値情報のコード変換表読み込み関数を作成する。
    """
    # キャッシュを準備。
    cache = {}
    def read_code_list(column_name: str) -> dict:
        """
        国土数値情報のコード変換表を読み込む。

        Args:
            column_name (str):
                対応表を読み込む列名。

        Returns:
            dict:
                {code: 対応する値}形式の辞書。
        """
        if column_name in cache:
            return cache[column_name]
        code_dict = _read_codelist_file(column_name)
        if code_dict is not None:
            cache[column_name] = code_dict
        return code_dict
    return read_code_list

# 読み込み関数を作成。
_read_codelist = _create_read_code_list_fun()


#-----------------------------------------------------------------------------
def _convert_code(df: pandas.DataFrame) -> pandas.DataFrame:
    """
    国土数値情報のコードを対応するデータに変換する。

    Args:
        df (DataFrame):
            変換するデータ。
            変換可能なデータが全て変換される。

    Returns:
        DataFrame:
            変換済みのデータ。
    """
    for i in df.columns:
        code_dict = _read_codelist(i)
        if code_dict is None:
            continue
        df[i] = [
            code_dict[code] if code in code_dict else numpy.NaN
            for code in df[i].astype(int)
        ]
    return df


#-----------------------------------------------------------------------------
def _rename_columns(
    df: pandas.DataFrame, conv_table: dict
) -> pandas.DataFrame:
    """
    国土数値情報の列名を変更する。

    Args:
        df (DataFrame):
            国土数値情報が含まれたテーブル。
        conv_table (dict):
            列名変換表。
            {"国土数値情報列名コード": "列名"} 形式。

    """
    df.columns = [conv_table[i] if i in conv_table else i for i in df.columns]
    return df


#-----------------------------------------------------------------------------
def cleanup(
    df: pandas.DataFrame, inplace: bool = False
) -> (None, pandas.DataFrame):
    """
    列名の変更とコードのデータへの変更を行い、国土数値情報の可読性を上げる。

    Args:
        df (pandas.DataFrame):
            整形するデータ。
        inplace (bool):
            Trueならコピーを作成せずにデータを書き換える。

    Value (pandas.DataFrame):
        inplaceがFalseなら整形したデータを返す。
    """
    if not inplace:
        df = df.copy()
    df = _convert_code(df)
    df = _rename_columns(df, _COLUMNS_JA)
    return df if not inplace else None
