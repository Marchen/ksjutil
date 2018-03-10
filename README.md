# ksjutil
国土数値情報を操作するパッケージ。  
現在のところ国土数値情の列名を読みやすく変更し、～～コードを値に変換する`cleanup()`関数が入っています。
<br>

# 依存
numpy, pandas
<br>

# 例
```Python
import geopandas
import ksjutil

gpd = geopandas.read_file("文化施設/P27-13.shp")
clean_gpd = ksjutil.cleanup(gpd)
clean_gpd.head()
```
<br>

# データの構造

## ディレクトリの構造
このパッケージでは列名やコード変更用のデータをフォルダとファイルで管理しています。  
データは`_data`ディレクトリ以下に下のような構造でに格納されています。
- _data
    - N03（識別子、この場合は行政区域）
        - 001（列番号、この場合はN03_001）
            - meta.json（列名データ）
            - year.txt（西暦year年のコードと対応するデータ）
        - 002
            - meta.json

   	- N02
        - 001
            - meta.json
        - 002
			- meat.json
            - year.txt
<br>

## ファイルの内容

### meta.json
`meta.json`は各列の変換情報を保持していて、年による違いを表現するため、以下のような構造になっています。将来日本語以外も追加できるように階層化してありますが、現状は日本語しか使っていません。
```JSON
{
	"ja": {
		"year": "name",
		"year": "name",
	}
}
```
例えば、[P12観光資源データ](http://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P12-v2_2.html)のP12_001は2010年のデータだと都道府県を、2014年のデータだと観光資源_IDを表します。よって、meta.jsonは以下のようになります。
```JSON
{
  "ja": {
    "2010": "都道府県",
    "2014": "観光資源_ID"
  }
}
```
ファイルの文字コードはUTF-8です。
<br>

### year.txt
`year.txt`は各年の～～コードと実際のデータの変換表です。  
年によってデータの内容が異なり、変換処理も異なるので、このようなデータ構造になっています。  
文字コードはUTF-8のタブ区切りテキストで、`code`列がコード、`data`列が変換先のデータです。  
変換しない方が扱いやすいので、今のところ県コード、自治体コードは意図的に変換していません。  
例えば、[都市公園](http://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P13.html)データの[公園種別コード](http://nlftp.mlit.go.jp/ksj/gml/codelist/CityParkCd.html)のデータは以下のようになります。  
```
code	data
1	街区公園
2	近隣公園
3	地区公園（カントリーパーク）
4	総合公園
5	運動公園
6	広域公園
7	レクリエーション都市
8	国営公園
9	特殊公園（風致公園、動植物公園、歴史公園、墓園）
10	緩衝緑地
11	都市緑地
12	緑道
13	都市林
14	広場公園
```
<br>
