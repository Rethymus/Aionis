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

## 终审更正（2026-08-24 深夜，openapi 主机实测可达后读到官方文本）

openapi.krx.co.kr **主机可达**（未被地域封锁），但其 "OPEN API" 实为 **Data Marketplace 付费数据市场**：
- 官方原文："데이터 상품을 선택하여 **결제를 완료**하시면 **심사 후** 데이터 용량에 따라 **이메일, 웹 다운로드 방식** 등으로 데이터를 받아보실 수 있습니다"（选品→**付款**→**审核**→邮件/网页下载交付）
- 支付 = 银行转账，입금자=주문자（汇款人须同订购人）；法人付款需另行邮件申请（krxdata@krx.co.kr）
- 学生/教职工/学校法人半价（需在学/在职证明）
- 即：**不存在免费注册 key**；官方唯一路线 = 付费购买（韩国支付通道 + 审核 + 文件式交付，非 API 端点）

## 续接路径（业主三选一）

A. **付费购买**（唯一官方）：业主经韩国支付通道购买 신용융자 数据商品（学术半价可享），文件交付后我方按文件摄取建管道。
B. **业主提供**任一可访问韩国网络的代理/VPN 出口 → 我方重测 data.krx.co.kr 四路线（封锁判定仅对本网络成立）。
C. **接受降级等价物**：仿 TACO→BTS 先例，指定一个业主认可的公开代理指标（若存在）。

## 已验证的技术要点（省去重新考古）

## 已验证的技术要点（省去重新考古）

- 目标数据屏：신용융자（融资）거래현황，**menuId=MDC0201020101，bld=`dbms/MDC/STAT/standard/MDCSTAT01501`**
- 查询参数：`locale=ko_KR&mktId=ALL&trdDd=YYYYMMDD&share=1&money=1&csvxls_isNo=false`
- 老门户 getJsonData/OTP-download 端点族 2026 年已全部加装会话强制（上表）——**Open API（openapi.krx.co.kr）是唯一可自动化路线**
- 编码注意：老门户 CSV 为 EUC-KR；Open API 返回 JSON（UTF-8）
- 礼貌：≥2s 间隔照旧
- 探针源码：scratch_krx_probe*.py（1-19）
