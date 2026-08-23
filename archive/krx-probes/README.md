# KRX 韩国散户杠杆 — 自动化封锁证据链与续接指南（2026-08-24 终审）

## 六条路线全部实证封锁（26 次探测，2026-08-24 终审补全）

| 补充路线 | 结果 | 判定 |
|---|---|---|
| FRED 序列搜索（korea margin/KOSPI credit/korea stock credit） | 仅银行净息差（DDEI01KRA…），无融资余额序列 | 无此数据 |
| BOK ECOS（网页 + API 主机） | 网页 chrome-error；API 主机 **TLS 握手层掐断**（SSLEOF，与 VanEck 同型地域封锁） | 网络层封锁 |

### 原 KRX 四路线

| 路线 | 结果 | 判定 |
|---|---|---|
| `getJsonData.cmd`（复刻浏览器序列：页面预热+Referer+XHR 头+bld 双位） | `LOGOUT`（6B）/ 400 | 服务端会话强制 |
| `download.cmd`（http，OTP 320 字符 token 已取得） | 引至门户公告页 | token 校验失败 |
| `download.cmd`（https 同流程） | `서비스 에러`（"服务器内部错误，请检查输入值"） | token 与 JS 建立的会话状态绑定 |
| 真浏览器（IAB）加载 menuId=MDC0201020101 | 壳可载、数据区永不完成渲染（快照 30s 超时） | 海外访问 + JS 重门户 |

## 续接路径（仅需业主一步）

1. 业主在 **openapi.krx.co.kr** 注册并获取 Open API key（韩国手机/事业者认证——会话内不可代办）。
2. 将 key 交给任意后续 session，按下方要点建管道：

## 已验证的技术要点（省去重新考古）

- 目标数据屏：신용융자（融资）거래현황，**menuId=MDC0201020101，bld=`dbms/MDC/STAT/standard/MDCSTAT01501`**
- 查询参数：`locale=ko_KR&mktId=ALL&trdDd=YYYYMMDD&share=1&money=1&csvxls_isNo=false`
- 老门户 getJsonData/OTP-download 端点族 2026 年已全部加装会话强制（上表）——**Open API（openapi.krx.co.kr）是唯一可自动化路线**
- 编码注意：老门户 CSV 为 EUC-KR；Open API 返回 JSON（UTF-8）
- 礼貌：≥2s 间隔照旧
- 探针源码：scratch_krx_probe*.py（1-19）
