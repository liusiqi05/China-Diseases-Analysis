import os
from typing import List, Optional
import requests
import json
import socket
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get('DB_URL')
if not DB_URL:
    # 尝试从 .env 文件或系统环境读取
    raise RuntimeError('请在环境变量中设置 DB_URL，例如: mysql+pymysql://user:pass@host:3306/dbname')

engine = create_engine(DB_URL, pool_pre_ping=True)

app = FastAPI(title='Map Data API')

# 省级近似经纬度中心（用于当数据库没有经纬度列时，后端填充）
# 键以常见英文省名/直辖市名为主，必要时可扩展或改为中文键
PROVINCE_CENTROIDS = {
    # 直辖市
    'Beijing': (116.4074, 39.9042), '北京': (116.4074, 39.9042),
    'Tianjin': (117.200983, 39.084158), '天津': (117.200983, 39.084158),
    'Shanghai': (121.473701, 31.230416), '上海': (121.473701, 31.230416),
    'Chongqing': (106.551644, 29.563761), '重庆': (106.551644, 29.563761),
    # 省份（常用近似中心点）
    'Hebei': (114.4995, 38.0358), '河北': (114.4995, 38.0358),
    'Shanxi': (112.549248, 37.857014), '山西': (112.549248, 37.857014),
    'Liaoning': (123.429096, 41.796767), '辽宁': (123.429096, 41.796767),
    'Jilin': (125.3245, 43.886841), '吉林': (125.3245, 43.886841),
    'Heilongjiang': (127.9688, 45.368), '黑龙江': (127.9688, 45.368),
    'Jiangsu': (118.767413, 32.041544), '江苏': (118.767413, 32.041544),
    'Zhejiang': (120.153576, 30.287459), '浙江': (120.153576, 30.287459),
    'Anhui': (117.282699, 31.866942), '安徽': (117.282699, 31.866942),
    'Fujian': (119.296494, 26.074508), '福建': (119.296494, 26.074508),
    'Jiangxi': (115.858197, 28.682892), '江西': (115.858197, 28.682892),
    'Shandong': (118.000, 36.500), '山东': (118.000, 36.500),
    'Henan': (113.6654, 34.757975), '河南': (113.6654, 34.757975),
    'Hubei': (112.23813, 30.335165), '湖北': (112.23813, 30.335165),
    'Hunan': (112.982279, 28.19409), '湖南': (112.982279, 28.19409),
    'Guangdong': (113.2806, 23.1252), '广东': (113.2806, 23.1252),
    'Hainan': (110.33119, 20.031971), '海南': (110.33119, 20.031971),
    'Sichuan': (104.065735, 30.659462), '四川': (104.065735, 30.659462),
    'Guizhou': (106.713478, 26.578343), '贵州': (106.713478, 26.578343),
    'Yunnan': (102.712251, 25.040609), '云南': (102.712251, 25.040609),
    'Shaanxi': (108.948024, 34.263161), '陕西': (108.948024, 34.263161),
    'Gansu': (103.823557, 36.058039), '甘肃': (103.823557, 36.058039),
    'Qinghai': (101.778916, 36.623178), '青海': (101.778916, 36.623178),
    'Ningxia': (106.278179, 38.46637), '宁夏': (106.278179, 38.46637),
    'Xinjiang': (87.617733, 43.792818), '新疆': (87.617733, 43.792818),
    'Tibet': (91.132212, 29.660361), '西藏': (91.132212, 29.660361),
    'Inner Mongolia': (111.670801, 40.818311), '内蒙古': (111.670801, 40.818311),
    'Guangxi': (108.320004, 22.82402), '广西': (108.320004, 22.82402),
    'Hong Kong': (114.109497, 22.396428), '香港': (114.109497, 22.396428),
    'Macau': (113.551526, 22.198745), '澳门': (113.551526, 22.198745),
    'Taiwan': (121.509062, 25.044332), '台湾': (121.509062, 25.044332)
}


class DiseaseItem(BaseModel):
    name: str
    value: List[float]  # [lng, lat]
    cases: Optional[int] = None
    raw: Optional[dict] = None


class ProvinceCases(BaseModel):
    name: str
    cases: Optional[int] = 0


class LocationCounts(BaseModel):
    name: str
    lng: Optional[float] = None
    lat: Optional[float] = None
    counts: Optional[dict] = {}


@app.get('/api/china_disease', response_model=List[ProvinceCases])
def get_china_disease():
    try:
        # 按 Province 汇总 Reported_Cases（字段名按你的表结构），返回省份名与病例数
        with engine.connect() as conn:
            # 注意：字段名大小写/下划线请根据实际表结构调整
            q = text('''
                SELECT Province AS name, SUM(Reported_Cases) AS cases
                FROM china_disease_data
                GROUP BY Province
                ORDER BY cases DESC
            ''')
            result = conn.execute(q)
            # 使用 mappings() 获得字典风格的结果，避免 Row 对象的属性访问差异
            items = []
            for row in result.mappings():
                name = row.get('name') or row.get('Province')
                cases = row.get('cases')
                try:
                    cases = int(cases) if cases is not None else 0
                except Exception:
                    cases = 0
                items.append({'name': name, 'cases': cases})
            return items
    except SQLAlchemyError as e:
        # 打印到控制台以便调试
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        # 捕获所有其他异常并打印堆栈，便于诊断
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/disease_locations', response_model=List[LocationCounts])
def get_disease_locations():
    """
    尝试返回每个地点（或城市/省）的各病种计数与经纬度（如果可用）。
    实现策略：先检查表中可用的列名，然后根据可用列聚合出
    name, lng, lat, disease, cases 的中间结果，再在后端将相同地点聚合为 counts 字段。
    若无法找到病种列，则会回退为按 Province 的汇总（与 /api/china_disease 类似），返回只有 name 与 cases。
    """
    try:
        with engine.connect() as conn:
            # 先检测表的列名
            db_name = engine.url.database
            cols_q = text("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=:db AND table_name='china_disease_data'")
            cols_res = conn.execute(cols_q, {'db': db_name})
            cols = [r[0] for r in cols_res.fetchall()]

            # 简单的列名匹配器（case-insensitive）
            lowcols = {c.lower(): c for c in cols}

            # 可能的列名候选
            disease_col = None
            for cand in ['disease', 'disease_type', 'diseaseName', 'Disease', 'Type']:
                if cand.lower() in lowcols:
                    disease_col = lowcols[cand.lower()]
                    break

            # 经纬度候选
            lng_col = None
            lat_col = None
            for cand in ['lng', 'longitude', 'lon', '经度', 'lng_x']:
                if cand.lower() in lowcols:
                    lng_col = lowcols[cand.lower()]
                    break
            for cand in ['lat', 'latitude', '纬度', 'lat_y']:
                if cand.lower() in lowcols:
                    lat_col = lowcols[cand.lower()]
                    break

            # 地点名称候选（city/location/name/province）
            name_col = None
            for cand in ['location', 'city', 'place', 'name', 'province', '区域', '地区']:
                if cand.lower() in lowcols:
                    name_col = lowcols[cand.lower()]
                    break

            reported_col = None
            for cand in ['reported_cases', 'reportedcases', 'reported_cases', 'Reported_Cases', 'cases', 'count']:
                if cand.lower() in lowcols:
                    reported_col = lowcols[cand.lower()]
                    break

            if disease_col and name_col:
                # 我们可以按地点+病种聚合
                q = text(f"""
                    SELECT {name_col} AS name,
                           {lng_col or 'NULL'} AS lng,
                           {lat_col or 'NULL'} AS lat,
                           {disease_col} AS disease,
                           SUM({reported_col or 'Reported_Cases'}) AS cases
                    FROM china_disease_data
                    GROUP BY {name_col}, {lng_col or 'NULL'}, {lat_col or 'NULL'}, {disease_col}
                """)
                rows = conn.execute(q)
                # 聚合到 Python 结构：按地点分组，counts 为 disease->cases
                places = {}
                for r in rows.mappings():
                    pname = r.get('name')
                    if not pname:
                        continue
                    lng = r.get('lng')
                    lat = r.get('lat')
                    disease = r.get('disease')
                    cases = r.get('cases') or 0
                    try:
                        cases = int(cases)
                    except Exception:
                        cases = 0
                    if pname not in places:
                        places[pname] = {'name': pname, 'lng': float(lng) if lng is not None else None, 'lat': float(lat) if lat is not None else None, 'counts': {}}
                    places[pname]['counts'][str(disease)] = places[pname]['counts'].get(str(disease), 0) + cases

                # 尝试填充缺失的经纬度（按省/地点名匹配 PROVINCE_CENTROIDS）
                for p in places.values():
                    if (p.get('lng') is None or p.get('lat') is None) and isinstance(p.get('name'), str):
                        cent = PROVINCE_CENTROIDS.get(p['name']) or PROVINCE_CENTROIDS.get(p['name'].title())
                        if cent:
                            p['lng'], p['lat'] = cent[0], cent[1]
                return list(places.values())
            else:
                # 回退：按省/省份聚合（与 /api/china_disease 行为一致）
                q = text('''
                    SELECT Province AS name, SUM(Reported_Cases) AS cases
                    FROM china_disease_data
                    GROUP BY Province
                    ORDER BY cases DESC
                ''')
                result = conn.execute(q)
                out = []
                for row in result.mappings():
                    name = row.get('name') or row.get('Province')
                    cases = row.get('cases')
                    try:
                        cases = int(cases) if cases is not None else 0
                    except Exception:
                        cases = 0
                    obj = {'name': name, 'counts': {'all': cases}}
                    # 填充经纬度（若能从 PROVINCE_CENTROIDS 匹配）
                    if isinstance(name, str):
                        cent = PROVINCE_CENTROIDS.get(name) or PROVINCE_CENTROIDS.get(name.title())
                        if cent:
                            obj['lng'], obj['lat'] = cent[0], cent[1]
                        else:
                            obj['lng'], obj['lat'] = None, None
                    out.append(obj)
                return out
    except SQLAlchemyError as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/region_analysis')
def region_analysis(regions: Optional[str] = None, debug: Optional[bool] = False):
    """
    返回一个或多个省/地区的分析汇总：年龄分布、性别分布、是否患病/确诊情况、季节分布、临床结果、社会活动因素等。
    请求参数：regions（可选，逗号分隔的中文或英文省名），若不提供则返回所有数据的汇总。
    返回格式：[{ region: '四川', total: 123, age_distribution: {...}, gender: {...}, disease_status: {...}, season: {...}, clinical: {...}, social: {...} }, ...]
    """
    try:
        with engine.connect() as conn:
            db_name = engine.url.database
            cols_q = text("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=:db AND table_name='china_disease_data'")
            cols_res = conn.execute(cols_q, {'db': db_name})
            cols = [r[0] for r in cols_res.fetchall()]
            lowcols = {c.lower(): c for c in cols}
            # debug 信息：列检测与选择
            debug_info = {'detected_columns': cols, 'lowcols_keys': list(lowcols.keys()), 'chosen': {}}

            # candidate columns - prefer the actual CSV headers we saw in your file
            # province column (support both English and Chinese header)
            province_col = lowcols.get('province') or lowcols.get('province_name') or lowcols.get('区域') or lowcols.get('地区') or 'Province'

            # age: your CSV uses Age_Group (strings like '0-14','15-24','65+')
            age_col = lowcols.get('age_group') or lowcols.get('age') or lowcols.get('年龄')

            # gender
            gender_col = lowcols.get('gender') or lowcols.get('sex') or lowcols.get('性别')

            # status / confirmed flags: Lab_Confirmed, Reported_Cases, Reported (we'll use Lab_Confirmed if exists)
            status_col = lowcols.get('lab_confirmed') or lowcols.get('lab_confirm') or lowcols.get('lab_confirmed_flag') or None

            # date/month/season: CSV has Month, Year, Season columns
            date_col = lowcols.get('month') or lowcols.get('report_date') or lowcols.get('date') or None
            season_col = lowcols.get('season') or lowcols.get('季节') or None

            # clinical outcome / recovered / deaths columns
            clinical_col = lowcols.get('recovered') or lowcols.get('clinical_result') or lowcols.get('outcome') or lowcols.get('结果')

            # social / exposure-like columns (Contact_Tracing, Travel_History, Comorbidity)
            social_col = lowcols.get('contact_tracing') or lowcols.get('travel_history') or lowcols.get('exposure') or lowcols.get('social_activity')

            # reported cases column (counts)
            reported_col = lowcols.get('reported_cases') or lowcols.get('cases') or lowcols.get('count') or None

            # 将选择的列记录到 debug_info
            debug_info['chosen']['province_col'] = province_col
            debug_info['chosen']['age_col'] = age_col
            debug_info['chosen']['gender_col'] = gender_col
            debug_info['chosen']['status_col'] = status_col
            debug_info['chosen']['date_col'] = date_col
            debug_info['chosen']['season_col'] = season_col
            debug_info['chosen']['clinical_col'] = clinical_col
            debug_info['chosen']['social_col'] = social_col
            debug_info['chosen']['reported_col'] = reported_col

            # parse regions (support Chinese names passed from frontend). Provide a small mapping
            cn_to_en = {
                '北京':'Beijing','上海':'Shanghai','天津':'Tianjin','重庆':'Chongqing',
                '四川':'Sichuan','河南':'Henan','广东':'Guangdong','北京':'Beijing',
                '上海':'Shanghai','江苏':'Jiangsu','浙江':'Zhejiang','山东':'Shandong',
                '湖南':'Hunan','湖北':'Hubei','云南':'Yunnan','贵州':'Guizhou',
                '陕西':'Shaanxi','广西':'Guangxi','内蒙古':'Inner Mongolia','黑龙江':'Heilongjiang',
                '吉林':'Jilin','辽宁':'Liaoning','河北':'Hebei','山西':'Shanxi',
                '安徽':'Anhui','福建':'Fujian','江西':'Jiangxi','海南':'Hainan',
                '天津':'Tianjin','新疆':'Xinjiang','西藏':'Tibet','宁夏':'Ningxia',
                '香港':'Hong Kong','澳门':'Macau','台湾':'Taiwan'
            }

            region_list = None
            if regions:
                parsed = [r.strip() for r in regions.split(',') if r.strip()]
                # map Chinese names to English where possible, but allow either
                region_list = [cn_to_en.get(r, r) for r in parsed]
            # helper to run simple group queries
            def run_group(query, params=None):
                params = params or {}
                rows = conn.execute(text(query), params)
                res = {}
                for r in rows.mappings():
                    k = list(r.values())[0]
                    v = list(r.values())[1]
                    res[str(k) if k is not None else 'null'] = int(v or 0)
                return res

            # build where clause for region
            def region_where(col_name, region):
                return f"{col_name} = :region"

            targets = region_list if region_list else [None]
            out = []
            for reg in targets:
                where_clause = ''
                params = {}
                if reg:
                    where_clause = f"WHERE {province_col} = :region"
                    params['region'] = reg

                # total count: prefer summing the reported/cases column when available to match /api/disease_locations
                count_col_expr = (debug_info['chosen'].get('reported_col') or reported_col) or 'Reported_Cases'
                total_q = text(f"SELECT SUM({count_col_expr}) as cnt FROM china_disease_data {where_clause}")
                total = int(conn.execute(total_q, params).fetchone()[0] or 0)

                # age distribution buckets
                age_dist = {}
                if age_col:
                    # Your CSV uses Age_Group values like '0-14','15-24', '65+'; sum by bucket value
                    q = f"SELECT {age_col} AS bucket, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {age_col}"
                    rows = conn.execute(text(q), params)
                    for r in rows.mappings():
                        k = r.get('bucket')
                        c = int(r.get('c') or 0)
                        age_dist[str(k)] = c

                # gender
                gender_counts = {}
                if gender_col:
                    q = f"SELECT {gender_col} AS g, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {gender_col}"
                    gender_counts = run_group(q, params)

                # disease/status
                status_counts = {}
                if status_col:
                    q = f"SELECT {status_col} AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {status_col}"
                    status_counts = run_group(q, params)

                # season: prefer explicit Season column; fallback to Month mapping
                season_counts = {}
                # detect disease column to allow per-disease breakdown
                disease_col = lowcols.get('disease') or lowcols.get('disease_type') or lowcols.get('disease_name') or lowcols.get('diseasename') or lowcols.get('type') or None
                debug_info['chosen']['disease_col'] = disease_col
                if season_col:
                    q = f"SELECT {season_col} AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {season_col}"
                    season_counts = run_group(q, params)
                elif date_col:
                    # if date_col is numeric month, use it; if it's Year/Month string this may not apply
                    # try Month() if column is a date; otherwise if it's numeric month name 'Month' just group by it
                    try:
                        q = f"SELECT MONTH({date_col}) AS m, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY MONTH({date_col})"
                        rows = conn.execute(text(q), params)
                        month_map = {1:'Winter',2:'Winter',12:'Winter',3:'Spring',4:'Spring',5:'Spring',6:'Summer',7:'Summer',8:'Summer',9:'Autumn',10:'Autumn',11:'Autumn'}
                        seasons = {}
                        for r in rows.mappings():
                            m = r.get('m')
                            c = int(r.get('c') or 0)
                            season = month_map.get(int(m), 'Unknown') if m else 'Unknown'
                            seasons[season] = seasons.get(season, 0) + c
                        season_counts = seasons
                    except Exception:
                        # fallback: try treating the column as integer month or direct grouping
                        q = f"SELECT {date_col} AS m, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {date_col}"
                        season_counts = run_group(q, params)

                # clinical result
                clinical_counts = {}
                if clinical_col:
                    q = f"SELECT {clinical_col} AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {clinical_col}"
                    clinical_counts = run_group(q, params)
                else:
                    # fallback: use Recovered / Deaths if present
                    if 'recovered' in lowcols:
                        q = f"SELECT Recovered AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY Recovered"
                        clinical_counts = run_group(q, params)
                    elif 'deaths' in lowcols:
                        q = f"SELECT Deaths AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY Deaths"
                        clinical_counts = run_group(q, params)

                # social activity / exposure
                social_counts = {}
                if social_col:
                    q = f"SELECT {social_col} AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {social_col}"
                    social_counts = run_group(q, params)
                else:
                    # try Contact_Tracing, Travel_History, Comorbidity
                    for fallback in ['contact_tracing','travel_history','comorbidity']:
                        if fallback in lowcols:
                            q = f"SELECT {lowcols[fallback]} AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {lowcols[fallback]}"
                            social_counts = run_group(q, params)
                            break

                # --- 额外的区域级别聚合（增强前端所需的维度） ---
                # 检测可能存在的列并在可能时计算汇总值。所有操作仅使用 SELECT。
                extra = {}
                try:
                    # 简单列候选检测
                    deaths_col = lowcols.get('deaths') or lowcols.get('death')
                    recovered_col = lowcols.get('recovered') or lowcols.get('recovery')
                    hosp_col = lowcols.get('hospitalized') or lowcols.get('hospital') or lowcols.get('icu_admission')
                    vacc_col = lowcols.get('vaccinated') or lowcols.get('vaccine')
                    travel_col = lowcols.get('travel_history') or lowcols.get('travel')
                    quarant_col = lowcols.get('quarantined') or lowcols.get('quarantine')
                    urbanr_col = lowcols.get('urban_rural') or lowcols.get('urban')

                    # 症状类列（根据 COLUMN_SYNONYMS 建议的标准列名）
                    fever_col = lowcols.get('symptom_fever') or lowcols.get('symptom_fever')
                    cough_col = lowcols.get('symptom_cough') or lowcols.get('symptom_cough')
                    rash_col = lowcols.get('symptom_rash') or lowcols.get('symptom_rash')

                    # 住院天数
                    days_col = lowcols.get('days_hospitalized') or lowcols.get('days_hospital')

                    # region-level simple sums (如果存在相应列则直接汇总)
                    def safe_sum(colname, is_flag=False):
                        """
                        安全求和：
                        - 如果 is_flag 为 False，则直接对列做 SUM(col)
                        - 如果 is_flag 为 True，则把该列视为文本型的布尔标志（例如 'Yes'/'No'），
                          使用 CASE WHEN LOWER(TRIM(col)) IN (...) THEN count_col_expr ELSE 0 END 进行条件聚合
                        """
                        try:
                            if not colname:
                                return 0
                            if not is_flag:
                                q = text(f"SELECT SUM({colname}) FROM china_disease_data {where_clause}")
                            else:
                                # 标准真值集合（兼容中文/大小写/空白）
                                truth_vals_local = ("yes", "y", "1", "true", "是")
                                truth_list_local = ",".join([f"'{v}'" for v in truth_vals_local])
                                # 使用 count_col_expr 作为计数或权重表达式
                                q = text(f"SELECT SUM(CASE WHEN LOWER(TRIM({colname})) IN ({truth_list_local}) THEN {count_col_expr} ELSE 0 END) FROM china_disease_data {where_clause}")
                            r = conn.execute(q, params).fetchone()
                            return int(r[0] or 0)
                        except Exception:
                            return 0

                    extra['deaths'] = safe_sum(deaths_col)
                    # recovered/hospitalized/vaccinated 在你的 CSV 中是 Yes/No 标志，
                    # 因此使用基于真值的条件聚合（is_flag=True）来统计实际的病例数
                    extra['recovered'] = safe_sum(recovered_col, is_flag=True)
                    extra['hospitalized'] = safe_sum(hosp_col, is_flag=True)
                    extra['vaccinated'] = safe_sum(vacc_col, is_flag=True)

                    # travel / quarantine: 分组汇总，以便前端展示分布（如有）
                    travel_summary = {}
                    # 1) 原始分布（若存在列），2) 同时计算标准化的 Yes 计数（大小写/空白无关，接受常见真值）
                    truth_vals = ("yes","y","1","true","是")
                    if travel_col:
                        q = f"SELECT {travel_col} AS v, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {travel_col}"
                        travel_summary = run_group(q, params)
                        # 计算标准化的 "Yes" 计数
                        truth_list = ",".join([f"'{v}'" for v in truth_vals])
                        q_yes = f"SELECT SUM(CASE WHEN LOWER(TRIM({travel_col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS yes_sum FROM china_disease_data {where_clause}"
                        try:
                            r = conn.execute(text(q_yes), params).fetchone()
                            travel_summary['Yes'] = int(r[0] or 0)
                        except Exception:
                            travel_summary['Yes'] = travel_summary.get('Yes', 0)
                    elif 'travel_history' in lowcols:
                        col = lowcols['travel_history']
                        q = f"SELECT {col} AS v, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {col}"
                        travel_summary = run_group(q, params)
                        truth_list = ",".join([f"'{v}'" for v in truth_vals])
                        q_yes = f"SELECT SUM(CASE WHEN LOWER(TRIM({col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS yes_sum FROM china_disease_data {where_clause}"
                        try:
                            r = conn.execute(text(q_yes), params).fetchone()
                            travel_summary['Yes'] = int(r[0] or 0)
                        except Exception:
                            travel_summary['Yes'] = travel_summary.get('Yes', 0)
                    extra['travel_history'] = travel_summary

                    quarantine_summary = {}
                    if quarant_col:
                        q = f"SELECT {quarant_col} AS v, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {quarant_col}"
                        quarantine_summary = run_group(q, params)
                        truth_list = ",".join([f"'{v}'" for v in truth_vals])
                        q_yes = f"SELECT SUM(CASE WHEN LOWER(TRIM({quarant_col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS yes_sum FROM china_disease_data {where_clause}"
                        try:
                            r = conn.execute(text(q_yes), params).fetchone()
                            quarantine_summary['Yes'] = int(r[0] or 0)
                        except Exception:
                            quarantine_summary['Yes'] = quarantine_summary.get('Yes', 0)
                    extra['quarantined'] = quarantine_summary

                    # symptoms 汇总（针对存在的症状列，按 count_col_expr 做求和）
                    # 使用更严格且鲁棒的判定：仅当症状列标准化后等于 yes/真值集合时才计入。
                    symptoms = {}
                    truth_vals = ("yes", "y", "1", "true", "是")
                    truth_list = ",".join([f"'{v}'" for v in truth_vals])
                    if fever_col and fever_col in lowcols.values():
                        col = fever_col
                        q = f"SELECT SUM(CASE WHEN LOWER(TRIM({col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS c FROM china_disease_data {where_clause}"
                        try:
                            r = conn.execute(text(q), params).fetchone()
                            symptoms['fever'] = int(r[0] or 0)
                        except Exception:
                            symptoms['fever'] = 0
                    if cough_col and cough_col in lowcols.values():
                        col = cough_col
                        q = f"SELECT SUM(CASE WHEN LOWER(TRIM({col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS c FROM china_disease_data {where_clause}"
                        try:
                            r = conn.execute(text(q), params).fetchone()
                            symptoms['cough'] = int(r[0] or 0)
                        except Exception:
                            symptoms['cough'] = 0
                    if rash_col and rash_col in lowcols.values():
                        col = rash_col
                        q = f"SELECT SUM(CASE WHEN LOWER(TRIM({col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS c FROM china_disease_data {where_clause}"
                        try:
                            r = conn.execute(text(q), params).fetchone()
                            symptoms['rash'] = int(r[0] or 0)
                        except Exception:
                            symptoms['rash'] = 0
                    extra['symptoms'] = symptoms

                    # days hospitalized: sum/avg/count
                    dh = {'sum': 0, 'avg': 0.0, 'count': 0}
                    if days_col:
                        try:
                            q = text(f"SELECT SUM({days_col}) AS s, AVG({days_col}) AS a, COUNT({days_col}) AS c FROM china_disease_data {where_clause}")
                            r = conn.execute(q, params).fetchone()
                            dh['sum'] = int(r['s'] or 0) if r['s'] is not None else 0
                            try:
                                dh['avg'] = float(r['a']) if r['a'] is not None else 0.0
                            except Exception:
                                dh['avg'] = 0.0
                            dh['count'] = int(r['c'] or 0)
                        except Exception:
                            pass
                    extra['days_hospitalized'] = dh

                    # urban/rural breakdown
                    urb = {}
                    if urbanr_col:
                        q = f"SELECT {urbanr_col} AS v, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {urbanr_col}"
                        urb = run_group(q, params)
                    extra['urban_rural'] = urb

                    # monthly / timeseries: 若有 Month 或 date_col，则按月汇总
                    monthly = {}
                    month_col = None
                    if 'month' in lowcols:
                        month_col = lowcols['month']
                    elif date_col:
                        month_col = None
                    if month_col:
                        q = f"SELECT {month_col} AS m, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {month_col} ORDER BY {month_col}"
                        monthly = run_group(q, params)
                    elif date_col:
                        try:
                            q = f"SELECT MONTH({date_col}) AS m, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY MONTH({date_col}) ORDER BY MONTH({date_col})"
                            rows = conn.execute(text(q), params)
                            for r in rows.mappings():
                                m = r.get('m')
                                c = int(r.get('c') or 0)
                                monthly[str(int(m))] = c
                        except Exception:
                            monthly = {}
                    extra['monthly'] = monthly
                except Exception:
                    # 任何额外聚合失败都不要阻断主流程；记录为空
                    extra = {k: 0 for k in ['deaths','recovered','hospitalized','vaccinated']}

                # 把结果 append 到输出中
                out.append({
                    'region': reg or 'ALL',
                    'total': total,
                    'age_distribution': age_dist,
                    'gender': gender_counts,
                    'disease_status': status_counts,
                    'season': season_counts,
                    'clinical': clinical_counts,
                    'social': social_counts,
                    # 额外字段
                    'deaths': extra.get('deaths', 0),
                    'recovered': extra.get('recovered', 0),
                    'hospitalized': extra.get('hospitalized', 0),
                    'vaccinated': extra.get('vaccinated', 0),
                    'travel_history': extra.get('travel_history', {}),
                    'quarantined': extra.get('quarantined', {}),
                    'symptoms': extra.get('symptoms', {}),
                    'days_hospitalized': extra.get('days_hospitalized', {}),
                    'urban_rural': extra.get('urban_rural', {}),
                    'monthly': extra.get('monthly', {}),
                    # by_disease: per-disease breakdown for each dimension (filled below if possible)
                    'by_disease': {}
                })
                # If we have a disease column, compute per-disease breakdowns for this region
                if disease_col:
                    # build initial disease totals
                    per_idx = { }
                    qd = f"SELECT {disease_col} AS disease, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                    rowsd = conn.execute(text(qd), params)
                    for r2 in rowsd.mappings():
                        dname = r2.get('disease')
                        key = str(dname) if dname is not None else 'Unknown'
                        per_idx[key] = {'total': int(r2.get('c') or 0), 'age_distribution': {}, 'gender': {}, 'season': {}, 'clinical': {}, 'social': {}}

                    # age buckets per disease
                    if age_col:
                        q = f"SELECT {disease_col} AS disease, {age_col} AS bucket, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {age_col}"
                        for r3 in conn.execute(text(q), params).mappings():
                            dn = r3.get('disease')
                            key = str(dn) if dn is not None else 'Unknown'
                            b = r3.get('bucket')
                            c = int(r3.get('c') or 0)
                            if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                            per_idx[key]['age_distribution'][str(b)] = per_idx[key]['age_distribution'].get(str(b),0) + c

                    # gender per disease
                    if gender_col:
                        q = f"SELECT {disease_col} AS disease, {gender_col} AS g, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {gender_col}"
                        for r3 in conn.execute(text(q), params).mappings():
                            dn = r3.get('disease')
                            key = str(dn) if dn is not None else 'Unknown'
                            g = r3.get('g')
                            c = int(r3.get('c') or 0)
                            if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                            per_idx[key]['gender'][str(g)] = per_idx[key]['gender'].get(str(g),0) + c

                    # season per disease (handle date_col->month->season mapping similarly)
                    if season_col:
                        q = f"SELECT {disease_col} AS disease, {season_col} AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {season_col}"
                        for r3 in conn.execute(text(q), params).mappings():
                            dn = r3.get('disease')
                            key = str(dn) if dn is not None else 'Unknown'
                            s = r3.get('s')
                            c = int(r3.get('c') or 0)
                            if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                            per_idx[key]['season'][str(s)] = per_idx[key]['season'].get(str(s),0) + c
                    elif date_col:
                        try:
                            q = f"SELECT {disease_col} AS disease, MONTH({date_col}) AS m, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, MONTH({date_col})"
                            month_map = {1:'Winter',2:'Winter',12:'Winter',3:'Spring',4:'Spring',5:'Spring',6:'Summer',7:'Summer',8:'Summer',9:'Autumn',10:'Autumn',11:'Autumn'}
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                m = r3.get('m')
                                c = int(r3.get('c') or 0)
                                season = month_map.get(int(m), 'Unknown') if m else 'Unknown'
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                per_idx[key]['season'][season] = per_idx[key]['season'].get(season,0) + c
                        except Exception:
                            pass

                    # clinical per disease
                    if clinical_col:
                        q = f"SELECT {disease_col} AS disease, {clinical_col} AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {clinical_col}"
                        for r3 in conn.execute(text(q), params).mappings():
                            dn = r3.get('disease')
                            key = str(dn) if dn is not None else 'Unknown'
                            s = r3.get('s')
                            c = int(r3.get('c') or 0)
                            if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                            per_idx[key]['clinical'][str(s)] = per_idx[key]['clinical'].get(str(s),0) + c

                    # social per disease
                    if social_col:
                        q = f"SELECT {disease_col} AS disease, {social_col} AS s, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {social_col}"
                        for r3 in conn.execute(text(q), params).mappings():
                            dn = r3.get('disease')
                            key = str(dn) if dn is not None else 'Unknown'
                            s = r3.get('s')
                            c = int(r3.get('c') or 0)
                            if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                            per_idx[key]['social'][str(s)] = per_idx[key]['social'].get(str(s),0) + c

                    # ----- 新增：按病种的额外聚合（deaths/recovered/hospitalized/vaccinated/symptoms/days/monthly/travel/quarantine） -----
                    try:
                        # 候选列（使用 lowcols 中的真实列名）
                        deaths_col = lowcols.get('deaths') or lowcols.get('death')
                        recovered_col = lowcols.get('recovered')
                        hosp_col = lowcols.get('hospitalized') or lowcols.get('icu_admission')
                        vacc_col = lowcols.get('vaccinated')
                        travel_col = lowcols.get('travel_history')
                        quarant_col = lowcols.get('quarantined')
                        fever_col = lowcols.get('symptom_fever')
                        cough_col = lowcols.get('symptom_cough')
                        rash_col = lowcols.get('symptom_rash')
                        days_col = lowcols.get('days_hospitalized')
                        month_col = lowcols.get('month')

                        # numeric sums per disease (if columns exist)
                        if deaths_col:
                            q = f"SELECT {disease_col} AS disease, SUM({deaths_col}) AS v FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('v') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                per_idx[key]['deaths'] = v

                        if recovered_col:
                            # recovered 字段在 CSV 中通常是 Yes/No 标志，使用标准化真值集合做条件聚合
                            truth_vals = ("yes", "y", "1", "true", "是")
                            truth_list = ",".join([f"'{v}'" for v in truth_vals])
                            q = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({recovered_col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS v FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('v') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                per_idx[key]['recovered'] = v

                        if hosp_col:
                            # hosp (hospitalized) 也可能是 Yes/No 标志，按真值条件聚合
                            truth_vals = ("yes", "y", "1", "true", "是")
                            truth_list = ",".join([f"'{v}'" for v in truth_vals])
                            q = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({hosp_col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS v FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('v') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                per_idx[key]['hospitalized'] = v

                        if vacc_col:
                            # vaccinated 字段也是标志型，使用真值条件聚合统计已接种的人数/计数
                            truth_vals = ("yes", "y", "1", "true", "是")
                            truth_list = ",".join([f"'{v}'" for v in truth_vals])
                            q = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({vacc_col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS v FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('v') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                per_idx[key]['vaccinated'] = v

                        # travel_history / quarantined: grouping per disease
                        if travel_col:
                            q = f"SELECT {disease_col} AS disease, {travel_col} AS v, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {travel_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                val = r3.get('v')
                                c = int(r3.get('c') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                if 'travel_history' not in per_idx[key]: per_idx[key]['travel_history'] = {}
                                per_idx[key]['travel_history'][str(val)] = per_idx[key]['travel_history'].get(str(val),0) + c
                            # 另外计算标准化的 Yes 计数（大小写/空白无关，接受常见真值）
                            q_yes = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({travel_col})) IN ('yes','y','1','true','是') THEN {count_col_expr} ELSE 0 END) AS yes_sum FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q_yes), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('yes_sum') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                if 'travel_history' not in per_idx[key]: per_idx[key]['travel_history'] = {}
                                # 将标准化结果放在键 'Yes' 下，便于前端读取
                                per_idx[key]['travel_history']['Yes'] = v

                        if quarant_col:
                            q = f"SELECT {disease_col} AS disease, {quarant_col} AS v, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {quarant_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                val = r3.get('v')
                                c = int(r3.get('c') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                if 'quarantined' not in per_idx[key]: per_idx[key]['quarantined'] = {}
                                per_idx[key]['quarantined'][str(val)] = per_idx[key]['quarantined'].get(str(val),0) + c
                            # 标准化的 Yes 计数
                            q_yes = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({quarant_col})) IN ('yes','y','1','true','是') THEN {count_col_expr} ELSE 0 END) AS yes_sum FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q_yes), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('yes_sum') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                if 'quarantined' not in per_idx[key]: per_idx[key]['quarantined'] = {}
                                per_idx[key]['quarantined']['Yes'] = v

                            # urban_rural per disease: group by disease and urban_rural value
                            if urbanr_col:
                                q = f"SELECT {disease_col} AS disease, {urbanr_col} AS v, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {urbanr_col}"
                                for r3 in conn.execute(text(q), params).mappings():
                                    dn = r3.get('disease')
                                    key = str(dn) if dn is not None else 'Unknown'
                                    val = r3.get('v')
                                    c = int(r3.get('c') or 0)
                                    if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                    if 'urban_rural' not in per_idx[key]: per_idx[key]['urban_rural'] = {}
                                    per_idx[key]['urban_rural'][str(val)] = per_idx[key]['urban_rural'].get(str(val),0) + c
                                # also compute standardized 'Urban'/'Rural' Yes-like counts if values are non-standard
                                try:
                                    q_yes = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({urbanr_col})) IN ('urban','城镇','town','city') THEN {count_col_expr} ELSE 0 END) AS urban_sum, SUM(CASE WHEN LOWER(TRIM({urbanr_col})) IN ('rural','农村','village') THEN {count_col_expr} ELSE 0 END) AS rural_sum FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                                    for r3 in conn.execute(text(q_yes), params).mappings():
                                        dn = r3.get('disease')
                                        key = str(dn) if dn is not None else 'Unknown'
                                        u = int(r3.get('urban_sum') or 0)
                                        rv = int(r3.get('rural_sum') or 0)
                                        if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                        if 'urban_rural' not in per_idx[key]: per_idx[key]['urban_rural'] = {}
                                        # only set when positive to avoid overwriting detailed buckets above
                                        if u > 0:
                                            per_idx[key]['urban_rural']['Urban'] = per_idx[key]['urban_rural'].get('Urban', 0) + u
                                        if rv > 0:
                                            per_idx[key]['urban_rural']['Rural'] = per_idx[key]['urban_rural'].get('Rural', 0) + rv
                                except Exception:
                                    pass

                        # symptoms: use conditional SUM of count_col_expr when symptom column is present
                        # symptoms per-disease: 使用标准化真值测试（LOWER(TRIM(...)) IN (...))，避免将 'No' 或其他非真值计入
                        truth_vals = ("yes", "y", "1", "true", "是")
                        truth_list = ",".join([f"'{v}'" for v in truth_vals])
                        if fever_col:
                            q = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({fever_col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS fever_sum FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('fever_sum') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                if 'symptoms' not in per_idx[key]: per_idx[key]['symptoms'] = {}
                                per_idx[key]['symptoms']['fever'] = v
                        if cough_col:
                            q = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({cough_col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS cough_sum FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('cough_sum') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                if 'symptoms' not in per_idx[key]: per_idx[key]['symptoms'] = {}
                                per_idx[key]['symptoms']['cough'] = v
                        if rash_col:
                            q = f"SELECT {disease_col} AS disease, SUM(CASE WHEN LOWER(TRIM({rash_col})) IN ({truth_list}) THEN {count_col_expr} ELSE 0 END) AS rash_sum FROM china_disease_data {where_clause} GROUP BY {disease_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                v = int(r3.get('rash_sum') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                if 'symptoms' not in per_idx[key]: per_idx[key]['symptoms'] = {}
                                per_idx[key]['symptoms']['rash'] = v

                        # days_hospitalized per disease: sum/avg/count
                        if days_col:
                            try:
                                q = text(f"SELECT {disease_col} AS disease, SUM({days_col}) AS s, AVG({days_col}) AS a, COUNT({days_col}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}")
                                for r3 in conn.execute(q, params).mappings():
                                    dn = r3.get('disease')
                                    key = str(dn) if dn is not None else 'Unknown'
                                    if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                    per_idx[key]['days_hospitalized'] = {'sum': int(r3.get('s') or 0), 'avg': float(r3.get('a') or 0.0), 'count': int(r3.get('c') or 0)}
                            except Exception:
                                pass

                        # monthly per disease
                        if month_col:
                            q = f"SELECT {disease_col} AS disease, {month_col} AS m, SUM({count_col_expr}) AS c FROM china_disease_data {where_clause} GROUP BY {disease_col}, {month_col}"
                            for r3 in conn.execute(text(q), params).mappings():
                                dn = r3.get('disease')
                                key = str(dn) if dn is not None else 'Unknown'
                                m = r3.get('m')
                                c = int(r3.get('c') or 0)
                                if key not in per_idx: per_idx[key] = {'total':0,'age_distribution':{},'gender':{},'season':{},'clinical':{},'social':{}}
                                if 'monthly' not in per_idx[key]: per_idx[key]['monthly'] = {}
                                per_idx[key]['monthly'][str(m)] = per_idx[key]['monthly'].get(str(m),0) + c
                    except Exception:
                        # 如果某些按病种聚合出错，不阻塞整体流程，继续保留已有 per_idx 部分
                        pass

                    # attach per_idx into the last appended out element
                    out[-1]['by_disease'] = per_idx
                    out[-1]['disease_list'] = list(per_idx.keys())

            if debug:
                return {'debug': debug_info, 'data': out}
            return out
    except SQLAlchemyError as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post('/api/deepseek_chat')
def deepseek_chat(payload: dict, debug: Optional[bool] = False):
    """Proxy endpoint to call Deepseek-like API.
    SECURITY: The server reads the API key from environment variable DEEPSEEK_API_KEY.
    Do NOT hardcode keys in frontend. This function assumes the remote API accepts a POST
    with JSON { messages: [...] } or { message: '...' } and returns JSON. Adjust as needed to match
    the actual Deepseek API.
    """
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise HTTPException(status_code=500, detail='DEEPSEEK_API_KEY not configured on server')
    # basic payload parsing
    msg = None
    if isinstance(payload, dict):
        msg = payload.get('message') or payload.get('prompt') or ''
    else:
        raise HTTPException(status_code=400, detail='invalid payload')

    # NOTE: The actual Deepseek API endpoint and request shape must be adapted.
    # Here we assume a generic endpoint; change to match provider documentation.
    api_url = os.environ.get('DEEPSEEK_API_URL') or 'https://api.deepseek.com/v1/chat'
    # simple DNS pre-check: ensure host resolves before making the request to give clearer errors
    try:
        host = None
        try:
            host = (api_url and api_url.startswith('http')) and __import__('urllib.parse').urlparse(api_url).hostname
        except Exception:
            host = None
        if host:
            try:
                socket.getaddrinfo(host, None)
            except Exception:
                raise HTTPException(status_code=502, detail=f'无法解析上游主机 {host}，请检查 DEEPSEEK_API_URL 是否正确且可达')
    except HTTPException:
        # 将 HTTPException 直接抛出以便返回友好错误
        raise
    except Exception:
        # 任何预检之外的错误不影响后续请求，继续执行
        pass
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    # 上游某些实现（参照错误）需要显式的 `model` 字段。优先使用客户端提供的 model，其次使用服务端环境变量 DEEPSEEK_MODEL，最后退回到常用安全默认。
    model = None
    if isinstance(payload, dict):
        model = payload.get('model')
    if not model:
        model = os.environ.get('DEEPSEEK_MODEL')
    if not model:
        # 选择一个通用默认以便快速验证；如果你有供应商指定的模型名，建议在环境变量 DEEPSEEK_MODEL 中设置
        model = os.environ.get('DEEPSEEK_DEFAULT_MODEL') or 'gpt-3.5-turbo'

    # 支持可选的 context/region_summary 字段：当提供时，我们把它作为 system message 前置，
    # 以便模型在生成回复时能利用后端提供的结构化上下文（例如地区摘要、表结构、查询结果等）。
    messages = []
    # payload 可能包含 context（任意 JSON）或 region_summary（字符串或 JSON）；优先 context
    context = None
    if isinstance(payload, dict):
        context = payload.get('context') or payload.get('region_summary')
    if context:
        try:
            # 如果 context 不是字符串，序列化为 json 文本以传递给模型
            if not isinstance(context, str):
                context_text = json.dumps(context, ensure_ascii=False)
            else:
                context_text = context
        except Exception:
            context_text = str(context)
        messages.append({'role': 'system', 'content': f'上下文(来自后端数据): {context_text}'})

    messages.append({'role': 'user', 'content': msg})

    body = {'model': model, 'messages': messages}
    try:
        resp = requests.post(api_url, headers=headers, json=body, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'proxy request failed: {e}')
    # 如果上游返回错误状态，尽量把状态码与响应体（截断）带回以便排查
    if resp.status_code >= 400:
        # 试着解析 json 以获得更有用的信息
        try:
            errj = resp.json()
        except Exception:
            errj = None
        if debug:
            # debug 模式下返回上游全部可用信息（注意：不要返回 API key）
            return {'upstream_status': resp.status_code, 'upstream_json': errj, 'upstream_text': resp.text}
        detail_msg = f'upstream status {resp.status_code}'
        if errj:
            detail_msg += f' json={errj}'
        elif resp.text:
            txt = resp.text
            if len(txt) > 1000:
                txt = txt[:1000] + '...'
            detail_msg += f' text={txt}'
        raise HTTPException(status_code=502, detail=detail_msg)

    try:
        j = resp.json()
    except Exception:
        # 非 JSON 响应也要把状态码包含进来，便于诊断
        txt = resp.text or ''
        if len(txt) > 1000:
            txt = txt[:1000] + '...'
        raise HTTPException(status_code=502, detail=f'bad response from remote (status {resp.status_code}): {txt}')

    # try to extract a reasonable reply; leave full JSON as fallback
    reply = None
    if isinstance(j, dict):
        # common shapes
        if 'reply' in j:
            reply = j['reply']
        elif j.get('choices') and isinstance(j.get('choices'), list) and j['choices'][0].get('message'):
            reply = j['choices'][0]['message'].get('content')
        elif j.get('result'):
            reply = j.get('result')
    if reply is None:
        # fallback: return entire json under 'raw'
        return { 'raw': j }
    return { 'reply': reply }


def _get_table_columns(table_name: str):
    """返回指定表的列名列表（小写）。用于把表结构传给 LLM 作为上下文说明。"""
    try:
        with engine.connect() as conn:
            db_name = engine.url.database
            q = text("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema=:db AND table_name=:tbl")
            rows = conn.execute(q, {'db': db_name, 'tbl': table_name}).fetchall()
            return [r[0] for r in rows]
    except Exception:
        return []


    


@app.get('/_routes')
def _list_routes():
    """调试用：列出当前注册的路由路径与方法，便于确认哪些端点可用。"""
    try:
        routes = []
        for r in app.routes:
            # 一些 route 对象 的属性名不同，尽量安全访问
            path = getattr(r, 'path', None) or getattr(r, 'url', None) or str(r)
            methods = list(getattr(r, 'methods', []) or [])
            routes.append({'path': path, 'methods': methods})
        return {'routes': routes}
    except Exception as e:
        return {'error': str(e)}


# 简单的疾病与性别同义词映射表（中文/常见别名 -> 数据库中常用值）
# 根据你的数据库实际值调整或扩展这些映射
DISEASE_SYNONYMS = {
    '艾滋病': 'HIV/AIDS',
    'hiv': 'HIV',
    '结核': 'TB',
    '肺结核': 'TB',
}

GENDER_SYNONYMS = {
    '男': 'Male', '男性': 'Male', 'm': 'Male', 'male': 'Male',
    '女': 'Female', '女性': 'Female', 'f': 'Female', 'female': 'Female'
}


def _apply_param_mappings(params: dict):
    """将已解析的 params 中的疾病/性别等值映射为后端期望的数据库值（就地修改并返回）。"""
    if not isinstance(params, dict):
        return params
    p = params
    # disease 映射（支持大小写不敏感匹配）
    if 'disease' in p and p['disease']:
        dv = str(p['disease']).strip()
        lk = dv.lower()
        if dv in DISEASE_SYNONYMS:
            p['disease'] = DISEASE_SYNONYMS[dv]
        elif lk in DISEASE_SYNONYMS:
            p['disease'] = DISEASE_SYNONYMS[lk]
    # gender 映射
    if 'gender' in p and p['gender']:
        gv = str(p['gender']).strip()
        lk = gv.lower()
        if gv in GENDER_SYNONYMS:
            p['gender'] = GENDER_SYNONYMS[gv]
        elif lk in GENDER_SYNONYMS:
            p['gender'] = GENDER_SYNONYMS[lk]
    return p


# 列名中英文映射（支持把用户常用中文名/别名映射为数据库列名）
# 请根据你的数据库实际列名调整右侧的值
COLUMN_SYNONYMS = {
    # province
    '省份': 'Province', '省': 'Province', 'province': 'Province', 'province_name': 'Province',
    # demographics / counts
    'deaths': 'Deaths', '死亡': 'Deaths',
    'age_group': 'Age_Group', '年龄分组': 'Age_Group', 'age': 'Age_Group',
    'hospitalized': 'Hospitalized', '住院': 'Hospitalized',
    'recovered': 'Recovered', '治愈': 'Recovered', '康复': 'Recovered',
    'month': 'Month', 'year': 'Year', 'season': 'Season', '季节': 'Season',
    'urban_rural': 'Urban_Rural', '城乡': 'Urban_Rural',
    'vaccinated': 'Vaccinated', '接种': 'Vaccinated',
    'travel_history': 'Travel_History', '旅行史': 'Travel_History',
    'comorbidity': 'Comorbidity', '合并症': 'Comorbidity',
    'quarantined': 'Quarantined', '隔离': 'Quarantined',
    'icu_admission': 'ICU_Admission', 'icu': 'ICU_Admission', 'ICU': 'ICU_Admission',
    'symptom_fever': 'Symptom_Fever', '发热': 'Symptom_Fever',
    'symptom_cough': 'Symptom_Cough', '咳嗽': 'Symptom_Cough',
    'symptom_rash': 'Symptom_Rash', '皮疹': 'Symptom_Rash',
    'contact_tracing': 'Contact_Tracing', '接触者追踪': 'Contact_Tracing',
    'lab_confirmed': 'Lab_Confirmed', '实验室确诊': 'Lab_Confirmed',
    'follow_up': 'Follow_Up', '随访': 'Follow_Up',
    'days_hospitalized': 'Days_Hospitalized', '住院天数': 'Days_Hospitalized',
    'region_code': 'Region_Code', '地区编码': 'Region_Code',
}


# 省份中英文映射（简单表；可扩展）
PROVINCE_NAME_MAP = {
    '北京':'Beijing','上海':'Shanghai','天津':'Tianjin','重庆':'Chongqing','四川':'Sichuan','河南':'Henan','广东':'Guangdong',
    '江苏':'Jiangsu','浙江':'Zhejiang','山东':'Shandong','湖南':'Hunan','湖北':'Hubei','云南':'Yunnan','贵州':'Guizhou',
    '陕西':'Shaanxi','广西':'Guangxi','内蒙古':'Inner Mongolia','黑龙江':'Heilongjiang','吉林':'Jilin','辽宁':'Liaoning','河北':'Hebei','山西':'Shanxi',
    '安徽':'Anhui','福建':'Fujian','江西':'Jiangxi','海南':'Hainan','新疆':'Xinjiang','西藏':'Tibet','宁夏':'Ningxia',
    '香港':'Hong Kong','澳门':'Macau','台湾':'Taiwan'
}


def _map_param_keys_and_values(params: dict):
    """把 params 的键（中文/别名）映射为数据库列名，并对省份值做中英映射等规范化。
    返回新的 params dict（不修改原始对象）。"""
    if not isinstance(params, dict):
        return params
    out = {}
    for k,v in params.items():
        if not k:
            continue
        key = str(k).strip()
        lk = key.lower()
        # 先按 COLUMN_SYNONYMS 映射键名
        mapped_key = None
        if key in COLUMN_SYNONYMS:
            mapped_key = COLUMN_SYNONYMS[key]
        elif lk in COLUMN_SYNONYMS:
            mapped_key = COLUMN_SYNONYMS[lk]
        else:
            # 如果原本就是数据库列名（大小写不同），尝试规范化首字母大写形式
            mapped_key = key
        # 规范化值：若是省份则映射为英文名（数据库可能用英文）
        new_val = v
        try:
            if mapped_key in ('Province', 'province'):
                sv = str(v).strip()
                if sv in PROVINCE_NAME_MAP:
                    new_val = PROVINCE_NAME_MAP[sv]
                else:
                    # 尝试大小写/首字母形式
                    if sv.title() in PROVINCE_NAME_MAP.values():
                        new_val = sv.title()
            # 其他字段的值映射（使用已有映射函数）
            # 让 _apply_param_mappings 处理 disease/gender
        except Exception:
            new_val = v
        out[mapped_key] = new_val
    # 再对 disease/gender 做值映射
    try:
        out = _apply_param_mappings(out)
    except Exception:
        pass
    return out


@app.post('/api/ai_generate_sql')
def ai_generate_sql(payload: dict):
    """第一步：让 AI 生成参数化的只读 SQL 查询。

    请求体示例: { "question": "...", "table": "china_disease_data", "model": "deepseek-chat" }
    返回: { "sql": "SELECT ... WHERE province = :region", "params": {"region": "Sichuan"}, "explain": "可选解释文本" }
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='invalid payload')
    question = payload.get('question')
    table = payload.get('table') or 'china_disease_data'
    if not question:
        raise HTTPException(status_code=400, detail='missing question')

    # 读取表结构并构造 system prompt，要求模型只返回 JSON 且不要执行任何 destructive 操作
    cols = _get_table_columns(table)
    cols_text = ', '.join(cols) if cols else 'unknown'
    # 在 system prompt 中加入同义词映射提示，帮助模型生成与数据库值一致的参数
    mapping_hints = []
    try:
        mapping_hints = [f"'{k}' -> '{v}'" for k,v in DISEASE_SYNONYMS.items()]
    except Exception:
        mapping_hints = []

    system_msg = (
        f"你是一名负责把自然语言问题翻译为参数化 SQL 查询的助手。\n"
        f"目标表: {table}。表的列: {cols_text}.\n"
        "规则: 仅生成只读 SELECT 查询。禁止 INSERT/UPDATE/DELETE/CREATE/DROP/ALTER。\n"
        "查询必须使用参数占位符的形式 :paramName（命名参数），不要直接插入用户文本，避免 SQL 注入。\n"
        "输出要求: 仅返回一个有效的 JSON 对象（不带其他注释），格式: {\n"
        "  \"sql\": \"<parameterized SQL string>\",\n"
        "  \"params\": { <paramName>: <value>, ... },\n"
        "  \"explain\": \"(可选) 解释文本\"\n"
        "}\n"
        "示例: {\"sql\":\"SELECT Province, SUM(Reported_Cases) AS cases FROM china_disease_data WHERE Province = :region GROUP BY Province\",\n"
        "           \"params\":{\"region\":\"Sichuan\"}}"
    )
    # 如果我们有同义词映射，则附加说明，告诉模型优先使用数据库的规范值
    if mapping_hints:
        system_msg += "\n注意：常见疾病名称映射（用户输入 -> 数据库值）： " + (", ".join(mapping_hints))
    # 列名映射提示
    try:
        col_hints = [f"'{k}' -> '{v}'" for k,v in COLUMN_SYNONYMS.items()]
        if col_hints:
            system_msg += "\n列名映射（常见中文/别名 -> 数据库列名）： " + (", ".join(col_hints))
    except Exception:
        pass
    # 省份中英文映射提示
    try:
        prov_hints = [f"'{k}' -> '{v}'" for k,v in PROVINCE_NAME_MAP.items()]
        if prov_hints:
            # 限制长度，避免提示过长：只列出前 10 项
            short = prov_hints[:10]
            system_msg += "\n省份映射（中文 -> 英文，部分示例）： " + (", ".join(short)) + (" ..." if len(prov_hints) > 10 else "")
    except Exception:
        pass

    # 组装消息并调用上游模型（复用 deepseek_chat 的发送逻辑）
    model = payload.get('model') or os.environ.get('DEEPSEEK_MODEL') or os.environ.get('DEEPSEEK_DEFAULT_MODEL') or 'gpt-3.5-turbo'
    api_url = os.environ.get('DEEPSEEK_API_URL') or 'https://api.deepseek.com/v1/chat'
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise HTTPException(status_code=500, detail='DEEPSEEK_API_KEY not configured on server')
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}

    messages = [
        {'role': 'system', 'content': system_msg},
        {'role': 'user', 'content': question}
    ]
    body = {'model': model, 'messages': messages}
    try:
        resp = requests.post(api_url, headers=headers, json=body, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'proxy request failed: {e}')
    if resp.status_code >= 400:
        try:
            errj = resp.json()
        except Exception:
            errj = resp.text
        raise HTTPException(status_code=502, detail={'upstream_status': resp.status_code, 'upstream': errj})
    try:
        j = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail='bad response from remote')

    # 提取模型生成的文本
    text_out = None
    if isinstance(j, dict):
        if j.get('choices') and isinstance(j.get('choices'), list) and j['choices'][0].get('message'):
            text_out = j['choices'][0]['message'].get('content')
        elif 'reply' in j:
            text_out = j['reply']
        elif 'result' in j:
            text_out = j['result']
    if not text_out:
        # fallback: stringify
        text_out = json.dumps(j, ensure_ascii=False)

    # 模型应该返回纯 JSON；我们尝试解析第一个 JSON 对象
    try:
        parsed = json.loads(text_out)
    except Exception:
        # 有时候模型会带 markdown 或说明文字，尝试从文本中抽取 JSON 子串
        import re
        m = re.search(r"\{[\s\S]*\}", text_out)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                raise HTTPException(status_code=502, detail='model did not return valid JSON containing SQL and params')
        else:
            raise HTTPException(status_code=502, detail='model did not return JSON')

    # 基本验证
    if not isinstance(parsed, dict) or 'sql' not in parsed:
        raise HTTPException(status_code=502, detail='model did not provide required `sql` field')
    if 'params' in parsed and not isinstance(parsed['params'], dict):
        raise HTTPException(status_code=400, detail='params must be an object')

    # 在返回前尝试把 params 的键与值做一次映射/规范化（列名中英映射、省份名映射、疾病/性别值映射）
    try:
        if 'params' in parsed and isinstance(parsed['params'], dict):
            parsed['params'] = _map_param_keys_and_values(parsed['params'])
    except Exception:
        # mapping 失败不应阻塞主流程
        pass

    # 返回解析后对象，前端或下一步执行端点将进一步校验与执行
    return parsed


@app.post('/api/execute_sql')
def execute_sql(payload: dict):
    """第二步：安全执行参数化只读 SQL。

    请求体示例: { "sql": "SELECT ...", "params": { ... }, "max_rows": 200 }
    限制: 仅允许 SELECT，禁止分号和 DDL/DML 关键字；仅允许访问白名单表（当前默认 china_disease_data）。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='invalid payload')
    sql = payload.get('sql')
    params = payload.get('params') or {}
    max_rows = int(payload.get('max_rows') or 200)
    if not sql:
        raise HTTPException(status_code=400, detail='missing sql')

    # 基本安全检查
    import re
    lowered = sql.strip().lower()
    if ';' in sql:
        raise HTTPException(status_code=400, detail='semicolons are not allowed')
    # 只允许 SELECT 开头
    if not re.match(r'^\s*select\b', lowered, re.IGNORECASE):
        raise HTTPException(status_code=400, detail='only SELECT queries are allowed')
    # 禁止常见危险关键字
    for bad in ['insert ', 'update ', 'delete ', 'drop ', 'create ', 'alter ', 'truncate ', 'merge ']:
        if bad in lowered:
            raise HTTPException(status_code=400, detail=f'forbidden statement: {bad.strip()}')

    # 白名单表检查：确保查询只引用允许的表
    allowed_tables = { 'china_disease_data' }
    # 查找所有简单的 table tokens（粗略）
    tokens = re.findall(r"from\s+([\w\.]+)|join\s+([\w\.]+)", sql, flags=re.IGNORECASE)
    referenced = set()
    for a,b in tokens:
        if a:
            referenced.add(a.split('.')[-1])
        if b:
            referenced.add(b.split('.')[-1])
    # 如果找不到表名（例如子查询或复杂表达式），我们也允许，但会校验列是否来自白名单表 later by trusting the whitelist minimal
    if referenced and not referenced.issubset(allowed_tables):
        # 如果引用了非白名单表，拒绝执行
        bads = referenced - allowed_tables
        raise HTTPException(status_code=400, detail=f'reference to forbidden tables: {bads}')

    # 执行查询（使用 SQLAlchemy text 与命名参数）
    try:
        # 规范化绑定参数：模型或映射可能返回与 SQL 中占位符大小写不一致的键。
        # 在执行前把 params 转换为与 SQL 中占位符名字完全匹配的字典（大小写不敏感匹配）。
        import re as _re
        placeholder_names = _re.findall(r":(\w+)", sql)
        if placeholder_names:
            # 构建小写键到原值的映射以便做不区分大小写的查找
            params_lower = { (str(k).lower()): v for k, v in (params or {}).items() }
            params_for_exec = {}
            for pname in placeholder_names:
                if pname in params:
                    params_for_exec[pname] = params[pname]
                elif pname.lower() in params_lower:
                    params_for_exec[pname] = params_lower[pname.lower()]
                else:
                    # 未提供必要的绑定参数，返回 400 以便前端/调试
                    raise HTTPException(status_code=400, detail=f"missing bind parameter: {pname}")
        else:
            params_for_exec = params or {}

        with engine.connect() as conn:
            res = conn.execute(text(sql), params_for_exec)
            cols = list(res.keys())
            rows = []
            # fetch many but avoid unbounded fetch
            count = 0
            for r in res:
                if count >= max_rows:
                    break
                # 将 Row 转为普通 dict
                rows.append({c: (v if not isinstance(v, bytes) else v.decode('utf-8', errors='ignore')) for c,v in zip(cols, r)})
                count += 1
    except SQLAlchemyError as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    return {'columns': cols, 'rows': rows, 'row_count': len(rows)}


@app.post('/api/ai_sql_finalize')
def ai_sql_finalize(payload: dict):
    """可选：把 SQL 执行结果发回模型，让模型基于结果生成可读的最终回答。

    请求体示例: { "question": "...", "sql": "...", "params": {...}, "result": {columns:[..],rows:[...]}, "model": "deepseek-chat" }
    返回: { "reply": "..." }
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail='invalid payload')
    question = payload.get('question') or ''
    sql = payload.get('sql') or ''
    params = payload.get('params') or {}
    result = payload.get('result')
    model = payload.get('model') or os.environ.get('DEEPSEEK_MODEL') or os.environ.get('DEEPSEEK_DEFAULT_MODEL') or 'gpt-3.5-turbo'

    if not result:
        raise HTTPException(status_code=400, detail='missing result')

    # 构造系统提示：包含 question, sql, params, 以及 result（限制大小）
    # 为避免超长，把 rows 截断到前 100 条在发送给模型
    import copy
    safe_result = copy.deepcopy(result)
    try:
        if isinstance(safe_result.get('rows'), list) and len(safe_result['rows']) > 100:
            safe_result['rows'] = safe_result['rows'][:100]
    except Exception:
        pass

    system_msg = (
        f"你是一名数据分析助理。用户的问题: {question}\n"
        f"已生成并执行的 SQL: {sql}\n参数: {json.dumps(params, ensure_ascii=False)}\n"
        f"查询结果（已截断）: {json.dumps(safe_result, ensure_ascii=False)}\n"
        "任务: 基于上述结果，给出简洁、准确且面向非专业用户的回答；如果结果不足以直接回答，请说明需要哪些额外数据或澄清的问题。"
    )

    api_url = os.environ.get('DEEPSEEK_API_URL') or 'https://api.deepseek.com/v1/chat'
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        raise HTTPException(status_code=500, detail='DEEPSEEK_API_KEY not configured on server')
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    messages = [
        {'role': 'system', 'content': system_msg},
        {'role': 'user', 'content': f'请基于上面的结果回答: {question}'}
    ]
    body = {'model': model, 'messages': messages}
    try:
        resp = requests.post(api_url, headers=headers, json=body, timeout=30)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'proxy request failed: {e}')
    if resp.status_code >= 400:
        try:
            errj = resp.json()
        except Exception:
            errj = resp.text
        raise HTTPException(status_code=502, detail={'upstream_status': resp.status_code, 'upstream': errj})
    try:
        j = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail='bad response from remote')
    reply = None
    if isinstance(j, dict):
        if j.get('choices') and isinstance(j.get('choices'), list) and j['choices'][0].get('message'):
            reply = j['choices'][0]['message'].get('content')
        elif 'reply' in j:
            reply = j['reply']
        elif 'result' in j:
            reply = j['result']
    if reply is None:
        return {'raw': j}
    return {'reply': reply}
