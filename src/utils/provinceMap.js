// 省份中英文映射与归一化函数
const PROVINCE_NAME_MAP = {
  'Beijing': '北京','Shanghai': '上海','Guangdong': '广东','Guangxi': '广西','Jiangsu': '江苏','Zhejiang': '浙江',
  'Sichuan': '四川','Henan': '河南','Hunan': '湖南','Hubei': '湖北','Shandong': '山东','Yunnan': '云南',
  'Jiangxi': '江西','Hebei': '河北','Liaoning': '辽宁','Heilongjiang': '黑龙江','Anhui': '安徽','Fujian': '福建',
  'Chongqing': '重庆','Shaanxi': '陕西','Inner Mongolia': '内蒙古','Nei Mongol': '内蒙古','Tianjin': '天津',
  'Gansu': '甘肃','Guizhou': '贵州','Xinjiang': '新疆','Ningxia': '宁夏','Qinghai': '青海','Hainan': '海南',
  'Jilin': '吉林','Shanxi': '山西','Taiwan': '台湾','Hong Kong': '香港','Macau': '澳门'
}

export function mapProvinceName(name) {
  if (!name) return name
  let n = String(name).trim()
  // 去掉常见中文后缀（省/市/自治区/特别行政区 等）以便更容易匹配
  n = n.replace(/(省|市|自治区|特别行政区|回族自治区|维吾尔自治区|壮族自治区)$/g, '')
  // 如果已经包含中文字符，直接返回去除后缀后的名称
  if (/[\u4e00-\u9fa5]/.test(n)) return n
  if (PROVINCE_NAME_MAP[n]) return PROVINCE_NAME_MAP[n]
  const lower = n.toLowerCase()
  for (const k of Object.keys(PROVINCE_NAME_MAP)) {
    if (k.toLowerCase() === lower) return PROVINCE_NAME_MAP[k]
  }
  for (const k of Object.keys(PROVINCE_NAME_MAP)) {
    if (k.toLowerCase().includes(lower) || lower.includes(k.toLowerCase())) return PROVINCE_NAME_MAP[k]
  }
  return n
}

export default { mapProvinceName, PROVINCE_NAME_MAP }
