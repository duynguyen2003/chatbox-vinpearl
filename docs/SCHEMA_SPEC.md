# Đặc tả lược đồ cơ sở dữ liệu

Tài liệu này dành cho người **đọc để hiểu**, không phải để tra cứu cột.
Đặc tả kỹ thuật đầy đủ (từng cột, từng ràng buộc) nằm ở [DATABASE.md](DATABASE.md).

Ba câu hỏi được trả lời ở đây:

1. Lược đồ gồm những gì và mỗi bảng làm việc gì?
2. Vì sao lại thiết kế như vậy?
3. Vì sao gộp đúng ba chỗ mà không gộp thêm nữa?

---

# Phần 1 — Lược đồ có gì

## 1.1 Bối cảnh trong một đoạn

Chatbot tư vấn du lịch Vinpearl. Dữ liệu đầu vào là **23 file JSON cào từ vinpearl.com và
vinwonders.com**, chưa làm sạch. Đầu ra là **43 bảng PostgreSQL** (36 `core` + 7 `app`)
kèm **11 view đọc** trong schema `api`, chứa 4.223 dòng đã chuẩn hoá,
để agent tool truy vấn được bằng SQL thay vì đoán bằng tìm kiếm ngữ nghĩa.

Câu hỏi mà lược đồ này phải trả lời được — và file JSON thì không:

- *"Phòng 2 người ở Nha Trang dưới 3 triệu"* → cần lọc theo số và theo địa danh
- *"Ưu đãi nào còn hiệu lực tháng này"* → cần so sánh ngày
- *"Phòng hội nghị nào chứa 500 khách kiểu banquet"* → cần lọc theo kiểu bố trí

## 1.2 Bốn tầng

Lược đồ chia làm bốn tầng theo **vòng đời dữ liệu**, không phải theo chủ đề:

```
   TẦNG TRỤC          TẦNG NỘI DUNG           TẦNG ỨNG DỤNG        TẦNG VẬN HÀNH
   ─────────          ─────────────           ─────────────        ─────────────
   destination        property → room         app_user             ingest_run
   complex            attraction              session              data_quality_issue
   source             promotion               message
   brand              faq, policy             ticket
   media              golf, mice
   (8 bảng)           (26 bảng)               (7 bảng)             (2 bảng)
```

**Tầng trục** là thứ mọi bảng khác móc vào. Sai tầng này thì hỏng dây chuyền.
**Tầng nội dung** là dữ liệu nghiệp vụ thật.
**Tầng ứng dụng** ghi lại hoạt động của chatbot.
**Tầng vận hành** ghi lại chính quá trình nạp dữ liệu.

## 1.3 Xương sống quan hệ

```
core.
destination ─┬─< complex ─┬─< property ─┬─< room ·amenity_ids[] ┄> amenity
             │            │             └─< dining_service
             │            ├─< attraction ·itinerary        (tự tham chiếu)
             │            ├─< golf_course ─< golf_feature
             │            └─< mice_venue ─< mice_room ─< mice_room_capacity
             │
             └─< promotion_destination >─ promotion ·tags ─┬─< promotion_benefit
                                                          └─< 5 bảng con khác

policy_document ─┬─< policy_section     promotion ─┬─< promotion_section
                └─< policy_block                   └─< promotion_block

source ──< (mọi bảng nội dung)          brand ──< source, property, promotion

app.
app_user ─< session ─< message ─┬─< message_citation ┄┄> thực thể core (không FK)
                                └─── ticket

api.
hotel · room · promotion · attraction · golf_course · mice_venue ·
policy_document · faq · destination · data_health · promotion_active
```

`─<` khoá ngoại thật · `┄` liên kết bằng giá trị, database không ràng buộc ·
`·cột` dữ liệu nằm trong cột chứ không phải bảng riêng

Đọc sơ đồ: `A ─< B` nghĩa là *một A có nhiều B*.

## 1.4 Vai trò từng bảng

### Tầng trục — 8 bảng

| Bảng | Dòng | Vai trò |
|---|---:|---|
| `destination` | 13 | Địa danh hành chính (Nha Trang, Phú Quốc…). **Master data viết tay**, không sinh từ crawl |
| `destination_alias` | 32 | Bảng tra cứu tên. Cùng một nơi trong data có 26 cách viết khác nhau |
| `complex` | 8 | Khu phức hợp (Phu Quoc United Center…). Tầng giữa địa danh và sản phẩm |
| `source` | 131 | Mỗi URL đã cào là một dòng. Nền tảng để bot trích dẫn nguồn |
| `brand` | 7 | Vinpearl, VinWonders, Vinpearl Safari… |
| `entity_source` | 6 | Thực thể có nhiều nguồn (sân golf có 2 URL) |
| `page_link` | 603 | Đồ thị điều hướng website: trang A dẫn sang trang B |
| `media` | 768 | Mọi URL ảnh, dùng chung cho mọi loại thực thể |

### Tầng nội dung — 26 bảng

**Lưu trú (5)**

| Bảng | Dòng | Vai trò |
|---|---:|---|
| `property` | 15 | Khách sạn và resort |
| `room` | 116 | Loại phòng, kèm giá và diện tích |
| `amenity` | 50 | Từ điển tiện nghi (WIFI, bồn tắm…) |
| `room.amenity_ids` | 1.796 tham chiếu | Cột `TEXT[]` trỏ sang `amenity` (không FK) |
| `dining_service` | 68 | Nhà hàng trong khách sạn |

**Trải nghiệm (3)**

| Bảng | Dòng | Vai trò |
|---|---:|---|
| `attraction` | 78 | Công viên, show, trò chơi, sự kiện, hành trình — thứ đi được, chơi được. Lịch trình theo ngày nằm ở cột JSONB `itinerary` |
| `destination_highlight` | 28 | Nội dung **quảng cáo** ("3 lý do nên đến"), cố ý tách riêng |

**Golf và hội nghị (6)**

| Bảng | Dòng | Vai trò |
|---|---:|---|
| `golf_course` | 6 | Sân golf: số lỗ, par, người thiết kế |
| `golf_feature` | 67 | Tiện ích, trải nghiệm, giải thưởng và **bản đồ** của sân |
| `mice_venue` | 10 | Địa điểm tổ chức hội nghị |
| `mice_room` | 36 | Phòng hội nghị, kèm kích thước |
| `mice_room_capacity` | 191 | Sức chứa theo từng kiểu bố trí bàn ghế |

**Ưu đãi (11)**

| Bảng | Dòng | Vai trò |
|---|---:|---|
| `promotion` | 38 | Chương trình khuyến mãi, kèm 5 loại khoảng thời gian |
| `promotion_benefit` | 310 | Quyền lợi cụ thể (giảm 15%, tặng voucher…) |
| `promotion_destination` | 89 | Ưu đãi áp dụng ở địa danh nào |
| `promotion.tags` | 561 giá trị | Cột JSONB: loại ưu đãi, dịch vụ, kênh bán, nhóm khách, hạng thẻ |
| `promotion_code` | 45 | Mã giảm giá |
| `promotion_section` | 164 | Nội dung văn xuôi của trang ưu đãi |
| `promotion_block` | 507 | Bảng biểu, danh sách, tiêu đề trong trang |
| `policy_section` | 36 | Từng mục có tiêu đề trong văn bản |
| `policy_block` | 15 | Bảng biểu và danh sách trong văn bản |
| `promotion_term` | 188 | Điều khoản, quy tắc kết hợp, liên hệ và **bước đổi thưởng** |
| `promotion_relation` | 131 | Liên kết sang ưu đãi hoặc thương hiệu khác |
| `promotion_property_raw` | 327 | **Bảng kiểm dịch** — dữ liệu nguồn quá bẩn để dùng trực tiếp |

**Tri thức (6)**

| Bảng | Dòng | Vai trò |
|---|---:|---|
| `faq` | 171 | Câu hỏi thường gặp |
| `policy_document` | 7 | Văn bản điều khoản, quy định |
| `org_info` | 1 | Thông tin pháp nhân công ty (đúng một dòng) |
| `org_highlight` | 14 | Mục nổi bật trên trang giới thiệu |

### Tầng ứng dụng — 7 bảng

| Bảng | Vai trò |
|---|---|
| `app_user` | Người dùng. Chưa đăng nhập vẫn có một dòng |
| `session` | Phiên trò chuyện |
| `message` | Từng tin nhắn. **Nơi duy nhất lưu nội dung thô** |
| `message_citation` | Bot đã dùng nguồn nào để trả lời |
| `message_feedback` | Đánh giá của người dùng |
| `ticket` | Yêu cầu chuyển cho người thật xử lý |
| `event_log` | Nhật ký vận hành |

### Tầng vận hành — 2 bảng

| Bảng | Dòng | Vai trò |
|---|---:|---|
| `ingest_run` | 9 | Mỗi lần nạp dữ liệu là một dòng |
| `data_quality_issue` | 1.831 | **Mọi chỗ dữ liệu nguồn bị lỗi**, kèm vị trí chính xác trong file |

## 1.5 Cách đọc lược đồ khi cần trả lời một câu hỏi

Ví dụ: *"Khách sạn nào ở Hội An có phòng dưới 150 USD?"*

```
1. "Hội An"  →  destination_alias  →  destination.id = 'hoi-an'
2. destination  →  property  (lọc destination_id)
3. property     →  room      (lọc price_from_amount < 150)
4. room         →  source    (để trích dẫn link nguồn)
```

Bốn bước, đều là `JOIN` thường. Nếu để nguyên JSON thì bước 1 đã không làm được.

---

# Phần 2 — Vì sao thiết kế như vậy

## 2.1 Ba áp lực định hình lược đồ

**Áp lực 1: dữ liệu nguồn bẩn hơn vẻ ngoài.**

Không phải bẩn kiểu thiếu dấu cách. Bẩn kiểu *sai về ngữ nghĩa*:

| Phát hiện | Số liệu |
|---|---|
| Giá phòng thực chất là **số hotline** `1900232389` | 69/116 dòng |
| Đơn vị tiền tệ để trống dù `raw` ghi rõ "USD" | 116/116 dòng |
| Ưu đãi trùng lặp giữa các file | 124 dòng → **38 thực thể** |
| Tên khách sạn trong ưu đãi bị cắt cụt (`"Vinwonders Wave Park &"`) | 327 giá trị |
| Câu hỏi FAQ lặp y hệt | 3/174 |
| Đường dẫn máy người khác lộ trong data | 32 chỗ |

Nếu tin dữ liệu nguồn, bot sẽ báo giá phòng là **1,9 tỷ đồng**.

**Áp lực 2: bot phải trích dẫn được nguồn.**
Chatbot khách sạn nói sai giá là rủi ro nghiệp vụ. Nên mọi dòng phải truy ngược được về URL,
và kèm ngày quan sát.

**Áp lực 3: agent tool cần lọc bằng SQL.**
Tìm kiếm ngữ nghĩa không trả lời được *"dưới 3 triệu"*. Phải có cột số thật, kiểu dữ liệu thật.

## 2.2 Bảy quyết định quan trọng

### (1) Giữ cả giá trị thô lẫn giá trị đã phân tích

Mọi trường đo lường có **hai cột**: `price_from_amount` (số, để truy vấn) và `rate_raw`
(chuỗi gốc, để kiểm chứng).

> Chính nhờ giữ `raw` mà phát hiện được 69 phòng có "giá" là số hotline. Nếu chỉ lưu số đã
> parse, lỗi này vĩnh viễn không ai thấy.

### (2) Lỗi dữ liệu được ghi lại, không bị nuốt

Bảng `data_quality_issue` giữ mọi chỗ không parse được, kèm `json_path` trỏ đúng vị trí
trong file nguồn. Hiện có **1.831 dòng** qua 9 lần nạp.

Không có dòng nào biến mất trong im lặng.

### (3) `destination` là master data viết tay

Đây là bảng **duy nhất** không sinh từ crawl. Lý do: data có 26 cách viết cho cùng một nơi
(`Hanoi`, `Hà Nội`, `ha_noi`, `ha-noi`…), và `Nationwide` thì **không phải địa danh**.

Máy không tự quyết được `Nam Hoi An` là địa danh hay khu phức hợp. Người quyết.

### (4) Thêm tầng `complex` sau khi khảo sát website thật

Ban đầu lược đồ nối thẳng điểm tham quan vào khách sạn. Kiểm chứng: **0/68 khớp**.

Khảo sát vinpearl.com cho biết lý do — Vinpearl bán hàng theo **khu phức hợp**, và
khách sạn với công viên là **anh em trong cùng một khu**, không phải cha con.

> Đây là ví dụ điển hình: không có bằng chứng thì không được bịa quan hệ.

### (5) Không tin trạng thái ưu đãi đã cào

Trường `promotion_status` được tính lúc `2026-08-01` — cũ ngay khi nạp vào. Lược đồ hạ nó
xuống thành `status_at_crawl` chỉ để tham chiếu, còn trạng thái thật tính bằng view
`promotion_active` theo `CURRENT_DATE`.

### (6) Tách nội dung quảng cáo khỏi nội dung sản phẩm

Nguồn trộn lẫn *"Tata Show"* (có thật, mua vé được) với *"3 lý do bạn phải đến"* (câu quảng cáo).
Nếu để chung, bot sẽ trả lời câu hỏi *"Nha Trang có gì chơi"* bằng khẩu hiệu marketing.

→ 28 mục quảng cáo nằm riêng ở `destination_highlight`, ngoài đường đi của tìm kiếm.

### (7) Không xoá dòng, chỉ đánh dấu `is_active = false`

Mục biến mất khỏi website không bị `DELETE`, vì `message_citation` có thể đang trỏ tới nó —
xoá đi thì câu trả lời cũ mất nguồn.

## 2.3 Quy tắc chung: khi nào tách bảng, khi nào làm cột

Toàn bộ lược đồ tuân theo **một câu hỏi duy nhất**:

> Một dòng cha có thể có **nhiều** dòng con không?

| Trả lời | Kết quả | Ví dụ |
|---|---|---|
| Có nhiều (1–N) | **Bảng riêng** | Một khách sạn có nhiều phòng → `room` |
| Luôn 0 hoặc 1 | **Cột** | Một sân golf có một người thiết kế → `golf_course.designer` |

**Số dòng không phải tiêu chí.** `golf_course` chỉ có 6 dòng nhưng vẫn là bảng riêng, vì
6 sân đó có 61 tiện ích — quan hệ 1–N.

---

# Phần 3 — Đề xuất gộp bảng

## 3.1 Lược đồ đã gộp sẵn 6 chỗ

Nếu ánh xạ 1–1 từ cấu trúc JSON, lược đồ sẽ khoảng **60 bảng**. Nó xuống 48 vì đã gộp:

| Bảng | Gộp từ | Tiết kiệm |
|---|---|---:|
| `golf_feature` | 4 mảng: tiện ích, trải nghiệm, đặc điểm, giải thưởng | −3 bảng |
| `promotion.tags` | 5 chiều phân loại | −4 bảng |
| `promotion_term` | 3 mảng điều khoản | −2 bảng |
| `promotion_block` | bảng biểu + danh sách + tiêu đề | −2 bảng |
| `policy_block` | bảng biểu + danh sách | −1 bảng |
| `attraction` | 7 loại điểm tham quan | −6 bảng |

Nguyên tắc gộp: **cùng hình dạng, cùng cha, cùng lực lượng** → thêm cột `kind` rồi gộp.

## 3.2 Năm chỗ đã gộp: 48 → 43

### Gộp 1 — `promotion_step` vào `promotion_term`

```
promotion_term(promotion_id, kind, ord, text)   kind: term | combination | contact
promotion_step(promotion_id,       ord, text)   # đã gộp đi
```

Hình dạng **y hệt**, cùng cha, cùng lực lượng. Chỉ cần thêm `kind='step'`.

Đây là chỗ **thiếu nhất quán rõ ràng**: đã gộp 3 mảng vào `promotion_term` rồi mà lại để
`redemption_steps` riêng, không vì lý do gì cả.

### Gộp 2 — `golf_course_map` vào `golf_feature`

Bản đồ sân cũng chỉ là `{tên, ảnh}` gắn với một sân, giống hệt tiện ích và trải nghiệm.
Cần thêm cột `variant` để giữ `Marsh Course` / `Lake Course`.

### Gộp 3 — `attraction_itinerary_day` thành cột JSONB

Chỉ **7 dòng** thuộc 3 hành trình. Không ai truy vấn riêng một ngày, và bản thân
`activities` bên trong đã là văn bản tường thuật.

## 3.3 Vì sao KHÔNG gộp thêm nữa

Đây là phần quan trọng nhất của đề xuất.

### Lý do 1 — Gộp khác lực lượng thì sinh ra dữ liệu tự mâu thuẫn

Ví dụ gộp `golf_course` (6 dòng) với `golf_feature` (61 dòng) thành một bảng `golf`:

| name | designer | holes | par | feature_title |
|---|---|---|---|---|
| Vinpearl Golf Hai Phong | IMG Worldwide | 36 | 72 | Restaurant |
| Vinpearl Golf Hai Phong | IMG Worldwide | 36 | 72 | Pro Shop |
| Vinpearl Golf Hai Phong | IMG Worldwide | 36 | 72 | Golf Island… |
| *(lặp 10 lần cho mỗi sân)* | | | | |

Ba hậu quả:

- **Sửa một chỗ phải sửa 10 dòng.** Sót một dòng là dữ liệu mâu thuẫn với chính nó, và
  không có cách nào biết dòng nào đúng
- **`SELECT count(*) FROM golf` trả về 61, không phải 6.** Muốn đếm số sân phải `DISTINCT`
- **`par` và `holes` mất ý nghĩa** trên dòng mô tả một nhà hàng

### Lý do 2 — Gộp khác thuộc tính thì bảng đầy NULL

Nếu gộp `golf_course`, `mice_venue` và `property` thành một bảng "địa điểm":

| Cột | Dùng cho khách sạn | Dùng cho sân golf | Dùng cho hội nghị |
|---|---|---|---|
| `holes`, `par`, `designer` | NULL | ✓ | NULL |
| `room_page_url` | ✓ | NULL | NULL |
| `phone`, `overview` | NULL | NULL | ✓ |

Hậu quả kỹ thuật cụ thể:

- **Không đặt được `NOT NULL`** cho cột nào, vì mỗi loại cần cột khác nhau
- **Không đặt được `CHECK` có ý nghĩa** — `par` phải 70–73 với golf nhưng vô nghĩa với khách sạn
- Đây chính là các ràng buộc đã **bắt được 3 lỗi dữ liệu thật** khi nạp

Nói cách khác: gộp quá tay là **tự tháo bỏ lưới an toàn** của chính mình.

### Lý do 3 — Ít bảng không đồng nghĩa dễ quản lý

Một bảng 25 cột mà mỗi `kind` chỉ dùng 8 cột thì **khó đọc hơn** hai bảng 10 cột rõ ràng.

Cái thực sự làm lược đồ dễ quản lý là:

- **Tên có tiền tố theo miền**: `promotion_*`, `golf_*`, `mice_*`, `policy_*` — nhìn tên biết ngay thuộc về đâu
- **Mỗi bảng một việc rõ ràng**
- **Nhóm lại**: 43 bảng chia 8 nhóm là ~5 bảng mỗi nhóm, con số não người xử lý được
- **Tách schema**: `core` / `app` / `api` — ba thư mục thay vì một danh sách phẳng

Postgres hoàn toàn không quan tâm bạn có 20 hay 43 bảng. Chi phí thêm một bảng gần bằng 0;
chi phí của dữ liệu tự mâu thuẫn thì không.

### Lý do 4 — Có chỗ tách là do quyết định nghiệp vụ, không phải kỹ thuật

`destination_highlight` (28 dòng) hoàn toàn có thể là `attraction` với `kind='highlight'`.
Nhưng nhóm đã **cố ý tách** để bot tìm kiếm không bao giờ nhầm câu quảng cáo thành hoạt động
có thật. Gộp lại là xoá bỏ một quyết định đã cân nhắc.

Tương tự, `promotion_property_raw` (327 dòng) tách riêng vì dữ liệu quá bẩn để ép khoá ngoại —
đưa nó vào bảng chính sẽ làm hỏng cả lần nạp.

## 3.4 Tóm tắt đề xuất

| | Số bảng |
|---|---:|
| Ánh xạ 1–1 từ JSON | ~60 |
| Sau 6 lần gộp trong thiết kế ban đầu | **48** |
| Sau 3 lần gộp cùng-hình-dạng | **45** |
| Sau 2 lần gộp bảng-nối thành cột | **43** |
| Gộp thêm nữa | **không nên** — mất ràng buộc, sinh dữ liệu mâu thuẫn |

Ba lần gộp đầu (`promotion_step`, `golf_course_map`, `attraction_itinerary_day`)
thuộc loại **an toàn tuyệt đối**: cùng hình dạng, cùng cha, cùng lực lượng. Không mất
ràng buộc nào, không sinh cột NULL nào.

Hai lần sau **có trả giá**, và cái giá đó đã biết trước:

| Gộp | Cái mất | Cái thay thế |
|---|---|---|
| `room_amenity` → `room.amenity_ids[]` | FK sang `amenity` | Adapter chỉ ghi id vừa tạo + test kiểm mồ côi |
| `promotion_tag` → `promotion.tags` | CHECK 5 chiều phân loại | `build_tags()` chỉ sinh khoá từ `TAG_FIELDS` + test |

Postgres **không** có khoá ngoại cho phần tử mảng, và JSONB **không** có CHECK theo
khoá — đó là giới hạn thật của công cụ, không phải chuyện cấu hình. Bù lại là 2 bảng
ít đi, 2.357 dòng nối biến mất, và truy vấn còn gọn hơn:
`WHERE amenity_ids @> ARRAY['bathtub']` thay cho một JOIN.

### 3.3b Một lần gộp đã làm rồi **tách lại**

Bốn bảng `promotion_section` / `policy_section` / `promotion_block` / `policy_block`
từng được gộp thành hai bảng đa hình khoá theo `(entity_type, entity_id)`. Chạy
được, nạp đủ 722 dòng, rồi bỏ.

**Phép thử: đếm số loại chủ sở hữu.** Đa hình trả giá bằng ràng buộc — mất khoá
ngoại, mất `ON DELETE CASCADE`, DataGrip không vẽ được đường nối nên bảng treo lơ
lửng không rõ thuộc về ai. Cái giá đó **cố định** dù có 2 hay 20 loại chủ, còn lợi
ích thì tỉ lệ với số loại chủ.

| Bảng đa hình | Số loại chủ | Kết luận |
|---|---:|---|
| `media` | 8 | Hoà vốn thừa |
| `entity_source` | mở | Hoà vốn |
| `content_section` / `content_block` | **2** | Lỗ — đã bỏ |

Chi tiết ở [docs/DATABASE.md §14.1](DATABASE.md).

## 3.5 Cách rẻ hơn để "dễ quản lý": schema và view

Gộp bảng không phải cách duy nhất, cũng không phải cách rẻ nhất.

**Tách schema.** 41 bảng chia thành `core` (34) và `app` (7). DataGrip hiện hai thư
mục gập được thay vì một danh sách phẳng. Không đụng một dòng dữ liệu, không mất một
ràng buộc nào.

**Dựng view.** 11 view trong schema `api` gộp sẵn quan hệ: `api.hotel` trả về khách
sạn kèm phòng và nhà hàng dưới dạng JSON; `api.room` tra sẵn tên tiện nghi từ mảng id.
Code đọc thấy 11 view thay vì 34 bảng, mà bên dưới khoá ngoại vẫn nguyên.

Quy tắc: **`core.*` là bảng thật, `api.*` là cùng thứ đó đã gộp sẵn.**
