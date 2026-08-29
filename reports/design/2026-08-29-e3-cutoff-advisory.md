# E3 provider cutoff 阻塞:处理方案咨询(文献印证版)

- 日期:2026-08-29;状态:ADVISORY(供决策;推荐方案 A+B)
- 对象:轮㊱ 遗留的精确阻塞——E3 影子运行要求"供应商真实知识截止值",GLM 的该值尚无一手来源钉定
- 证据分级:**A = arXiv API 实检**(2026-08-29/本轮,摘要逐条核对);**B = 领域知识**(标注)。新增实检:GLM-4.5 技术报告(arXiv 2508.06471)、When Benchmarks Age、Mitigating Temporal Misalignment、Evaluating LLMs in Finance Requires Explicit Bias Consideration。

---

## 1. 可选处理方案与利弊

### 方案 A(推荐,主证据):供应商一手声明,双源交叉钉定
GLM-4.5 技术报告真实存在(arXiv 2508.06471,A 级实检:23T tokens 多阶段训练)。**处理**:取报告全文(§训练数据)的截止声明 + 官方文档/API 镜像页交叉,双源一致后填入 `config/e3_live_contracts.yaml` 新增的 `provider_cutoff_policy.provider_cutoff` 字段(接线已于轮㊱ 完成,`_load_provider_cutoff()` 就绪),并记录检索日期与出处链接。
- 优:与 Model Cards(2018)规范一致——截止日期本就是卡片应载字段;GPT-4 Technical Report **[B 级]** 开创了厂商声明数据截止的先例(2021-09);一次钉定,永久可溯。
- 缺:声明滞后于权重迭代(GLM 版本更替需重钉);厂商不公布则此路不通。

### 方案 B(推荐,作为 A 的验证层):经验探针定界
用事件探针二分模型知识边界(已知 2026-08-28 前后的一手事件,双盲提问),结果与 A 的声明对照。
- 优:不依赖厂商诚实;文献直接支持其必要性——**"Can LLMs Be Constrained to the Past?"(2026-06,A 级)** 证明提示词式截止不可靠,须经验验证;**Look-Ahead-Bench(2026-01,A 级)** 证明 Q&A 式测法不足、须工作流级探测。
- 缺:探针测"知识边界"而非"训练截止"本身,分辨率有限;构成额外工程。

### 方案 C(不推荐):换 provider 到可验证 cutoff 的模型
- 优:cutoff 文档可能更全。
- 缺:违反"GLM pinned"(业主 2026-07-30 D1 决策);重开 provider 决策=新的治理成本;SiliconFlow/ModelScope 托管的是同权重,cutoff 问题同源。

### 方案 D(现状,不推荐延续):维持 unknown → fail-closed 常驻
- "优":绝对安全(守卫按设计拒绝)。
- 缺:E3 停摆(见 §3);且 **"When Benchmarks Age"(2025-10,A 级)** 证明时间失配会系统性腐蚀评估——"等一等"不会自愈。

## 2. 处理了的收益

1. **E3 影子数据开始积累** → 唯一 powered 零泄漏确认路径激活;跨域同构印证:TS-Arena(2025-12,活体预注册平台)与 OpenPM(2026-08,可审计 PIT 评估)证明该形态是 2025-2026 的行业方向(A 级)。
2. **P1-2(LLM vintage 纪律)落地**:模型卡 vintage 字段可填;**"Evaluating LLMs in Finance Requires Explicit Bias Consideration"(2026-02,A 级)** 的判词——未做偏差考量的 LLM 金融结果"污染回测、使报告结果对任何部署主张无用"——反向定义了做了之后的结果**可部署主张**资格。
3. **治理文档闭环**:SR 11-7 [B 级] 三件套(清单/文档/验证)全部齐备;32K 卡分析(2024,A 级)批评的"文档不完整"在本项目转为机器校验。
4. **终端呈现有容器无数据的问题转为有数据**:预测-实现分差带、校准、horizon 稳健性三套图表将获得真前向数据流。

## 3. 不处理的后果

1. **确认性前瞻路径持续缺位**:E2 因 underpowered 被判不足以作确认(ADR-005 [仓内]),E3 是唯一补偿路径——停摆=项目的可证伪主张永远只有回溯证据,而回溯证据正是 Harvey 式多重检验批评的对象 [B 级]。
2. **lookahead 风险未量化**:DatedGPT(2026-03,A 级)实测 lookahead premium **26.4bp/σ**——unknown cutoff = 该溢价存在于事件边缘特征且不可修正。
3. **治理验证失败**:SR 11-7 [B 级] 要求模型出处可验证;unknown cutoff 直接不通过。**From Knowing to Doing(2026-05,A 级)**:长回测与训练数据重叠使 LLM agent 评估失效——不钉 cutoff 的任何 shadow 数据在文献标准下不可用。
4. **技术债显性化**:/model-health 与状态文件将长期显示"阻塞于一个可查证的值"——对以反泄漏立身的项目,这是品牌级伤痕;且 GLM 版本迭代会重置问题,越晚钉定越难比较历史。
5. **评估腐蚀的累积性**:**When Benchmarks Age(2025-10,A 级)**:时间失配随时间放大——影子数据的缺失是随日历时间复利的。

## 4. 建议决策(A+B 组合,四步)

1. 获取 GLM-4.5 报告全文(arXiv PDF/HTML),摘录训练数据截止声明(逐字);
2. 官方文档/API 镜像页第二来源交叉(JS 壳→用渲染代理或 models 端点);
3. 双源一致 → 填 `provider_cutoff` + 出处链接与检索日进 YAML(接线就绪);不一致或单源 → 落 B 探针;
4. 探针套件(8-10 个已知日期的一手事件,双盲)验证边界与声明一致 → 重跑 08-31 shadow 触发 → 影子数据入库。

**预计**:A 一步(若厂商声明可得)即解阻塞;B 为加固层,半天工程。
