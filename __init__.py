"""
ksj: 国土数値情報を操作するパッケージ

現在のところ国土数値情報をきれいにするcleanup()関数が入っている。

Depends:
    os, typing, numpy, pandas

Suggests:
    geopandas

例：

import geopandas
import ksjutil

gpd = geopandas.read_file("文化施設/P27-13.shp")
clean_gpd = ksjutil.cleanup(gpd)
clean_gpd.head()
"""

# =============================================================================
#   準備
# =============================================================================

import codecs
import itertools
import json
import os
from typing import Callable, Dict, Tuple
import warnings

import numpy
import pandas

from ._conv import G02

__all__ = ["cleanup"]



# =============================================================================
#   定数定義
# =============================================================================

# デフォルトの列名リスト。
_DEFAULT_COLNAME_FILE = "column_names.txt"

# 変換関数を読み込み。
_CONVERT_FUNCTIONS = [
    [2012, G02.LATEST_YEAR, G02.convert]
]


# =============================================================================
#   関数定義
# =============================================================================

# -----------------------------------------------------------------------------
def _convert_values(df: pandas.DataFrame, year: int) -> pandas.DataFrame:
    """
    データの値を変換する。

    Args:
        df (pandas.DataFrame):
            変換するデータ。
        year (int):
            変換するデータの年。
    """
    for y, latest_year, convert in _CONVERT_FUNCTIONS:
        if year == y or (year is None and y == latest_year):
            df = convert(df)
    return df


# -----------------------------------------------------------------------------
def _data_dir_path():
    """
    データディレクトリのパスを返す。
    """
    return os.path.join(os.path.dirname(__file__), "_data")


#------------------------------------------------------------------------------
def _read_default_column_name_conversion_table() -> Tuple[Dict[str, str]]:
    """
    列名対応表を読み込む。

    Returns:
        dict, dict:
            {"国土数値情報列名コード": "列名"}型の辞書。
            １番目の辞書が日本語、２番目が英語。
            ただし、英語はまだほとんど実装していない。
    """
    path = os.path.join(_data_dir_path(), _DEFAULT_COLNAME_FILE)
    df = pandas.read_csv(path, encoding = "utf_8",  sep = "\t")
    conv_ja = {key: value for key, value in zip(df["対応番号"], df["属性名"])}
    conv_en = {key: value for key, value in zip(df["対応番号"], df["name"])}
    return (conv_ja, conv_en)


#------------------------------------------------------------------------------
def _metadata_dir_path(column_name: str) -> str:
    """
    列名に対応したメタデータの存在するディレクトリのパスを返す。

    Args:
        column_name (str):
            列名。

    Returns:
        str:
            ディレクトリのパス。
    """
    subfolders = column_name.split("_")
    path = os.path.join(_data_dir_path(), *subfolders)
    return path


#------------------------------------------------------------------------------
def _read_column_metadata(column_name: str, language: str) -> Dict[str, str]:
    """
    列名に対応するメタデータを読み込んで整形する。

    Args:
        column_name (str):
            列名。
        language (str):
            言語コード。

    Returns:
        以下の形式のデータ。
        {
            "年（西暦）": "列名",
            "latest_year": "最新データの年",
            "default_name": "デフォルトの（最新データの）列名",
            "has_code_table": bool（コード変換表があるか）
        }
    """
    # メタデータを読み込む。
    root_dir = _metadata_dir_path(column_name)
    path = os.path.join(root_dir, "meta.json")
    with codecs.open(path, encoding = "utf_8") as f:
        metadata = json.load(f)
        if language in metadata:
            metadata = metadata[language]
        else:
            return
    # 最新のデータをデフォルトとして採用。
    latest_year = str(max([int(i) for i in metadata]))
    metadata["latest_year"] = latest_year
    metadata["default_name"] = metadata[latest_year]
    # 変換テーブルの存在を確認。
    files = os.listdir(root_dir)
    metadata["has_code_table"] = len(files) > 1
    return metadata


#------------------------------------------------------------------------------
def _create_column_metadata_list(language: str) -> Dict[str, dict]:
    """
    変換情報が存在する列に対応するメタデータ一覧を作成する。

    Args:
        lang (str):
            言語コード。

    Returns:
        dict:
            {"列名": {列のメタデータ}}形式のメタデータの一覧。
    """
    # 対応している国土数値情報の識別子一覧を作成する。
    data_names = os.listdir(_data_dir_path())
    data_names.remove(_DEFAULT_COLNAME_FILE)
    # サブフォルダを取得し、対応している列名の一覧を作成する。
    subfolders = {
        i: os.listdir(os.path.join(_data_dir_path(), i)) for i in data_names
    }
    column_names = [
        list(itertools.product([k], v)) for k, v in subfolders.items()
    ]
    column_names = list(itertools.chain.from_iterable(column_names))
    column_names = ["{0}_{1}".format(*i) for i in column_names]
    # 列のメタデータを読み込む。
    metadata = {
        i: _read_column_metadata(i, language) for i in column_names
        if _read_column_metadata(i, language) is not None
    }
    return metadata


#------------------------------------------------------------------------------
def _read_codelist_file(
   column_name: str, year: (int, str, None), language: str
) -> (None, Dict[int, str]):
    """
    コードとデータの変換表を読み込む。

    Args:
        column_name (str):
            変換するコードの列名。
        year (int, str, None):
            データの年。
        language (str):
            言語コード。

    Returns:
        None, dict:
            変換表が見つかった場合、{code: data}形式の辞書を返す。
            変換表が見つからない場合、Noneを返す。

    """
    column_list = _COLUMN_LIST[language]
    if not column_name in column_list:
        return
    if not column_list[column_name]["has_code_table"]:
        return
    year = column_list[column_name]["latest_year"] if year is None else year
    path = os.path.join(_metadata_dir_path(column_name), year + ".txt")
    codelist = pandas.read_csv(path, sep = "\t", encoding = "utf_8")
    return {code: data for code, data in zip(codelist.code, codelist.data)}


# -----------------------------------------------------------------------------
def _create_cached_code_list_fun() -> Callable:
    """
    キャッシュ機能付きの国土数値情報のコード変換表読み込み関数を作成する。
    """
    # キャッシュを準備。
    cache = {}
    def read_code_list(
        column_name: str, year: (int, str, None), language: str
    ) -> dict:
        """
        国土数値情報のコード変換表を読み込む。

        Args:
            column_name (str):
                対応表を読み込む列名。
            year (int, str, None):
                データの年。

        Returns:
            dict:
                {code: 対応する値}形式の辞書。
        """
        key = "{0}-{1}".format(column_name, str(year))
        if key in cache:
            return cache[key]
        code_dict = _read_codelist_file(column_name, year, language)
        if code_dict is not None:
            cache[key] = code_dict
        return code_dict
    return read_code_list

# 読み込み関数を作成。
_read_codelist = _create_cached_code_list_fun()


# -----------------------------------------------------------------------------
def _convert_code(
    df: pandas.DataFrame, year: (int, str, None), language: str
) -> pandas.DataFrame:
    """
    国土数値情報のコードを対応するデータに変換する。

    Args:
        df (DataFrame):
            変換するデータ。
            変換可能なデータが全て変換される。
        year (int, str, None):
            データの年。

    Returns:
        DataFrame:
            変換済みのデータ。
    """
    for i in df.columns:
        code_dict = _read_codelist(i, year, language)
        if code_dict is None:
            continue
        df[i] = [
            code_dict[code] if code in code_dict else pandas.NA
            for code in df[i]
        ]
    return df


# -----------------------------------------------------------------------------
def _find_column_name_from_data_dir(
    column_name: str, year: (int, str, None), language: str
) -> str:
    """
    詳細データから列名データを取得する。

    Args:
        column_name (str):
            国土数値情報の列名コード。
        year (int, str, None):
            データの年。Noneが指定された場合、最新の列名を返す。
        language (str):
            言語コード。

    Returns:
        str:
            変換した列名。
            変換する物が見つからない場合、元の列名（コード）を返す。
    """
    column_list = _COLUMN_LIST[language]
    if not column_name in column_list:
        return column_name
    if year is None:
        return column_list[column_name]["default_name"]
    if str(year) not in column_list[column_name]:
        warnings.warn(
            "Specified year not found in the data.\n"
            "Default column name was used for '{0}'.".format(column_name)
        )
        return column_list[column_name]["default_name"]
    return column_list[column_name][str(year)]


# -----------------------------------------------------------------------------
def _rename_columns(
    df: pandas.DataFrame, year: (int, str, None), conv_table: dict,
    language: str
) -> pandas.DataFrame:
    """
    国土数値情報の列名を変更する。

    Args:
        df (DataFrame):
            国土数値情報が含まれたテーブル。
        year (int, str, None):
            データの作成年度。
        conv_table (dict):
            列名変換表。
            {"国土数値情報列名コード": "列名"} 形式。
        language (str):
            言語コード。

    Returns:
        str:
            変換した列名。
    """
    # まずはちゃんとしたデータがある方のデータを使い、
    # データが見つからなかったときに一覧のデータを使う。
    df.columns = [
        _find_column_name_from_data_dir(i, year, language) for i in df.columns
    ]
    df.columns = [conv_table[i] if i in conv_table else i for i in df.columns]
    return df


# =============================================================================
#   データ準備
# =============================================================================

# 列名のメタデータ
_COLUMN_LIST = {
    "ja": _create_column_metadata_list("ja"),
    "en": _create_column_metadata_list("en")
}

# デフォルトの列名変換テーブル
_DEFAULT_COLUMNS = {
    lang: data for lang, data in
    zip(["ja", "en"], _read_default_column_name_conversion_table())
}


# =============================================================================
#   メイン関数。
# =============================================================================

# -----------------------------------------------------------------------------
def cleanup(
    df: pandas.DataFrame, year: (int, str, None) = None,
    inplace: bool = False, language: str = "ja"
) -> (None, pandas.DataFrame):
    """
    列名の変更とコードのデータへの変更を行い、国土数値情報の可読性を上げる。

    Args:
        df (pandas.DataFrame):
            整形するデータ。
        year (int, str, None):
            データの作成年度。
            例えば「P12-14_21.shp」だったら2014年。
            指定しない場合、データに存在する最新の列名が使われる。
        inplace (bool):
            Trueならコピーを作成せずにデータを書き換える。
        language (str):
            列名の言語。
            "ja"と"en"に対応。ただし、"en"はほとんどまだ実装していない。

    Value (pandas.DataFrame):
        inplaceがFalseなら整形したデータを返す。
    """
    if not inplace:
        df = df.copy()
    df = _convert_values(df, year)
    df = _convert_code(df, year, language)
    df = _rename_columns(df, year, _DEFAULT_COLUMNS[language], language)
    return df if not inplace else None
