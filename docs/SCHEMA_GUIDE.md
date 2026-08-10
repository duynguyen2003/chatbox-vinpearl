# Hướng dẫn đọc lược đồ cơ sở dữ liệu

Tài liệu này viết cho người **chưa từng đọc lược đồ này** và cần hiểu:
mỗi bảng lưu gì, vì sao lại chia như vậy, và nó ánh xạ từ chỗ nào trong file JSON gốc.

Ba tài liệu, ba mục đích khác nhau:

| Tài liệu | Dùng khi |
|---|---|
| **SCHEMA_GUIDE.md** (file này) | Muốn **hiểu** lược đồ — đọc từ đầu đến cuối |
| [SCHEMA_SPEC.md](SCHEMA_SPEC.md) | Muốn nắm nhanh thiết kế và lý do |
| [DATABASE.md](DATABASE.md) | Muốn **tra cứu** từng cột, từng ràng buộc |

---

# Phần A — Quan hệ tổng quan

## A.1 Ý tưởng trong một hình

Toàn bộ 43 bảng xoay quanh **một trục duy nhất**: địa danh. Mọi thứ khách hàng hỏi
("ở Nha Trang có gì", "Phú Quốc giá bao nhiêu") đều bắt đầu từ đó.

```
                          ┌─────────────┐
                          │ destination │  13 địa danh
                          │  (địa danh) │  ← master data viết tay
                          └──────┬──────┘
                                 │
                          ┌──────┴──────┐
                          │   complex   │  8 khu phức hợp
                          │ (khu tổ hợp)│  ← Phu Quoc United Center...
                          └──────┬──────┘
                                 │
        ┌──────────┬─────────────┼─────────────┬──────────────┐
        │          │             │             │              │
   ┌────┴────┐ ┌───┴──────┐ ┌────┴─────┐ ┌─────┴─────┐  ┌─────┴──────┐
   │property │ │attraction│ │golf_course│ │mice_venue │  │ promotion  │
   │khách sạn│ │điểm chơi │ │  sân golf │ │ hội nghị  │  │  ưu đãi    │
   │   15    │ │    78    │ │     6     │ │    10     │  │     38     │
   └────┬────┘ └──────────┘ └─────┬─────┘ └─────┬─────┘  └─────┬──────┘
        │                         │             │              │
   ┌────┴────┐              ┌─────┴──────┐ ┌────┴────┐   ┌─────┴──────┐
   │  room   │ 116          │golf_feature│ │mice_room│   │ 8 bảng con │
   │dining   │  68          │    67      │ │   36    │   │  ~1.700    │
   └─────────┘              └────────────┘ └─────────┘   └────────────┘
```

Song song với trục đó có **hai trục phụ**:

```
source (131)  ──► gắn vào MỌI bảng nội dung   → để bot trích dẫn được link nguồn
message_citation ──► trỏ ngược về thực thể     → để biết bot đã dùng nguồn nào trả lời
```

## A.2 Cách đọc ký hiệu

| Ký hiệu | Nghĩa | Ví dụ |
|---|---|---|
| `A ──< B` | Một A có **nhiều** B | Một khách sạn có nhiều phòng |
| `A >──< B` | Nhiều A ứng nhiều B, cần bảng nối | Một phòng có nhiều tiện nghi, một tiện nghi ở nhiều phòng |
| `A ──── B` | Một A ứng **một** B | Một tin nhắn có một đánh giá |

## A.3 Tra nhanh: câu hỏi của khách → bảng nào

| Khách hỏi | Đi qua các bảng |
|---|---|
| "Khách sạn ở Hội An dưới 150 USD?" | `destination_alias` → `destination` → `property` → `room` |
| "Có ưu đãi nào ở Phú Quốc còn hạn?" | `destination` → `promotion_destination` → `promotion_active` |
| "Phòng họp chứa 500 khách kiểu tiệc?" | `mice_room_capacity` → `mice_room` → `mice_venue` |
| "Nha Trang có gì chơi?" | `destination` → `attraction` (**không** lấy `destination_highlight`) |
| "Chính sách huỷ phòng thế nào?" | `policy_document` → `policy_section` |
| "Sân golf 18 lỗ ở đâu?" | `golf_course` (lọc `holes`) |

---

# Phần B — Chi tiết từng miền

Mỗi miền trình bày theo cùng một khuôn:
**JSON gốc trông thế nào → tách ra bảng nào → vì sao tách như vậy**.

## 1. Địa danh và khu phức hợp

### Lưu trữ cái gì

Danh sách nơi chốn, và bảng tra cứu để nhận ra chúng dù viết kiểu gì.

### JSON gốc

Địa danh **không có file riêng**. Nó nằm rải rác dưới nhiều tên khác nhau:

```jsonc
// data/hotel/...json
"location_name": "Bac Ninh"

// data/promotion/...json
"destinations": ["Nha Trang", "Phú Quốc", "Nationwide"]

// data/golf/golf.json
"location": { "destination": "Hai Phong", "city": "Hai Phong City" }

// data/entertainment/ha_noi.json
"destination": { "name": "Grand World Ocean City", "city": "Hanoi" }
```

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `destination` | Địa danh hành chính: `nha-trang`, `phu-quoc`, `ha-noi`… | 13 |
| `destination_alias` | Mọi cách viết của cùng một nơi | 32 |
| `complex` | Khu phức hợp: Phu Quoc United Center, Grand World Ocean City… | 8 |

### Vì sao chia như vậy

**Vì sao `destination` phải viết tay, không sinh từ crawl.** Data có **26 chuỗi khác nhau**
cho khoảng 13 nơi. Máy không phân biệt được `Hanoi` và `Hà Nội` là một, cũng không biết
`Nationwide` không phải địa danh. Đây là quyết định của người.

**Vì sao cần `destination_alias` riêng.** Nếu nhét các cách viết vào cột trong `destination`
thì mỗi lần crawler mang về cách viết mới lại phải thêm cột. Bảng riêng cho phép thêm dòng.

**Vì sao có thêm `complex`.** Trong file entertainment, trường `destination.name` thực chất là
**tên khu**, còn `city` mới là địa danh:

```jsonc
"destination": { "name": "Vu Yen Royal Island", "city": "Hai Phong" }
//                       ↑ khu phức hợp           ↑ địa danh
```

Lược đồ ban đầu gộp hai khái niệm này làm một, và đó là lý do **0/68** điểm tham quan khớp
được với khách sạn. Khảo sát vinpearl.com xác nhận: Vinpearl bán theo **khu**, khách sạn và
công viên là *anh em trong cùng khu*, không phải cha con.

---

## 2. Nguồn và xuất xứ

### Lưu trữ cái gì

Mọi URL đã cào, kèm thời điểm cào và ngôn ngữ của trang.

### JSON gốc

URL nằm lặp lại trong từng bản ghi:

```jsonc
"hotel_url": "https://vinpearl.com/en/hotels/vinpearl-hotel-bac-ninh",
"room_page_url": "https://vinpearl.com/en/hotels/vinpearl-hotel-bac-ninh/rooms",
"source_urls": ["https://vinpearl.com/en/vinpearl-golf-hai-phong", "..."]
```

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `source` | Mỗi URL một dòng, kèm `crawled_at`, `http_status`, ngôn ngữ | 131 |
| `entity_source` | Thực thể có **nhiều** nguồn | 6 |
| `page_link` | Trang A dẫn sang trang B — đồ thị điều hướng website | 603 |
| `brand` | Vinpearl, VinWonders, Vinpearl Safari… | 7 |
| `media` | Mọi URL ảnh | 768 |

### Vì sao chia như vậy

**Vì sao URL thành bảng riêng chứ không để làm cột chuỗi.** Ba lý do:

1. Cùng một URL xuất hiện ở nhiều bản ghi → để cột chuỗi là lặp dữ liệu
2. URL **có thuộc tính riêng**: cào lúc nào, trả về mã HTTP gì, tiếng Việt hay tiếng Anh
3. Ngôn ngữ phải **suy từ đường dẫn** `/vi/` hay `/en/`, không tin field `language` — file
   `nha-trang.json` khai `language: "en"` nhưng chứa **945 URL `/vi/`** so với 127 URL `/en/`

**Vì sao cần `entity_source` mà không chỉ một cột `source_id`.** Mỗi sân golf có **2 URL**,
và mỗi tiện ích con lại có `source_url` riêng. Đây là quan hệ nhiều–nhiều thật.

**Vì sao `media` không có khoá ngoại.** Sáu loại thực thể đều có ảnh. Tạo sáu bảng ảnh riêng
là ồn ào vô ích, nên dùng một bảng đa hình với `entity_type` + `entity_id`. Đánh đổi: mất
toàn vẹn tham chiếu, phải dọn dòng mồ côi bằng job định kỳ.

---

## 3. Lưu trú

### Lưu trữ cái gì

Khách sạn, loại phòng, tiện nghi trong phòng, và nhà hàng trong khách sạn.

### JSON gốc

```jsonc
{
  "hotel_id": "vinpearl-hotel-bac-ninh",
  "hotel_name": "Vinpearl Hotel Bac Ninh",
  "location_name": "Bac Ninh",
  "rooms": [
    { "room_id": "vinpearl-hotel-bac-ninh--room-1",
      "room_name": "Double Double Room",
      "guest_count": 4,
      "room_area":     { "raw": "37 m²", "square_meters": 37 },
      "price_from":    { "raw": "~ 131USD", "amount": 131, "currency": null },
      "standard_rate": { "raw": "tel:1900232389", "amount": 1900232389 },
      "amenities": ["Telephone", "WIFI", "Bathtub", "..."] }
  ],
  "dining_services": [
    { "service_id": "vinpearl-hotel-bac-ninh--dining-1",
      "service_name": "La Mia Casa",
      "opening_hours": { "raw": "6:00 - 22:00" } }
  ]
}
```

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `property` | Khách sạn / resort | 15 |
| `room` | Loại phòng: sức chứa, diện tích, giá, giường | 116 |
| `amenity` | Từ điển tiện nghi | 50 |
| `room.amenity_ids` | Cột mảng: phòng nào có tiện nghi nào | 1.796 tham chiếu |
| `dining_service` | Nhà hàng trong khách sạn | 68 |

### Vì sao chia như vậy

**`rooms[]` nằm trong `hotels[]` → tách bảng con.** Mảng object lồng nhau *chính là* quan hệ
1–N, chỉ viết bằng dấu ngoặc. Ở đây còn có bằng chứng thứ hai: **116/116** `room_id` bắt đầu
bằng `hotel_id + "--room-"`.

**`room_area: {raw, square_meters}` → hai cột, không phải bảng.** Object này không tồn tại độc
lập, không ai truy vấn "tất cả các room_area". Nó là thuộc tính của phòng.

**Vì sao giữ cả `raw` lẫn số đã phân tích.** Đây là quyết định cứu cả lược đồ:

> `standard_rate.raw` = `"tel:1900232389"` ở **69/116 dòng**. Crawler bắt nhầm link hotline
> thành giá, và điền luôn `amount = 1900232389`. Nếu chỉ lưu số đã phân tích, bot sẽ báo giá
> phòng 1,9 tỷ đồng. Nhờ giữ `raw` mà phát hiện được — **chỉ 47/116 phòng có giá thật**.

**`amenities[]` → bảng tra cứu + bảng nối.** 1.796 giá trị nhưng chỉ ~50 giá trị khác nhau
(`Telephone` 109 lần, `WIFI` 102 lần). Tỉ lệ lặp 36 lần/giá trị nghĩa là đây là **từ vựng
chung**, không phải văn bản tự do. Chuẩn hoá cho phép sửa `WIFI` → `Wi-Fi` một lần áp cho
102 dòng.

> Lưu ý dữ liệu bẩn: `bed_types` của nguồn có lẫn `"Bathtub"` — đó là tiện nghi, không phải
> giường. Adapter lọc bỏ.

---

## 4. Trải nghiệm và điểm tham quan

### Lưu trữ cái gì

Công viên, show diễn, trò chơi, sự kiện, hành trình gợi ý — và tách riêng nội dung quảng cáo.

### JSON gốc

Đây là miền **rối nhất**: 8 file, **3 thế hệ schema khác nhau**.

```jsonc
// Dạng A — key của sections là slug do parser tự đặt, tiếng Việt lẫn Anh
"sections": {
  "must_see_events":              { "items": [{ "name": "...", "time": "..." }] },
  "reasons_to_visit_grand_world": { "items": [{ "description": "..." }] },
  "tan_huong_mot_mua_he_mat_lanh_tai_cong_vien_nuoc_ha_tinh": { "items": [...] }
}

// Dạng B — thêm detail lồng bên trong mỗi item
"exclusive_experiences": { "items": [{ "title": "...", "detail": { "full_text": "..." } }] }

// Dạng C — có document_id, card_data, page_data, journey_data
"all_topics": [{ "card_data": {...}, "page_data": {...}, "journey_data": {...} }]
```

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `attraction` | Thứ **có thật, đi được**: công viên, show, trò chơi, sự kiện, hành trình | 78 |
| `destination_highlight` | Nội dung **quảng cáo**: "3 lý do nên đến", "Chào mừng đến…" | 28 |

Lịch trình theo ngày nằm ở cột JSONB `attraction.itinerary` — 3 hành trình, tổng 7 ngày.

### Vì sao chia như vậy

**Vì sao gộp 7 loại vào một bảng `attraction`.** Công viên, show, trò chơi, sự kiện… đều có
cùng bộ thuộc tính: tiêu đề, mô tả, ảnh, link chi tiết. Tách 7 bảng chỉ để phân biệt loại là
thừa — dùng cột `kind` là đủ.

**Vì sao adapter phải duyệt `sections.values()` chứ không hardcode key.** Key là slug do
parser tự đặt và **không thống nhất** giữa các file — có key tiếng Việt dài 47 ký tự. Hardcode
là chắc chắn sót.

**Vì sao tách `destination_highlight` ra khỏi `attraction`.** Đây là **quyết định nghiệp vụ**,
không phải kỹ thuật. Nguồn trộn lẫn hai loại nội dung:

| Loại | Ví dụ | Thuộc bảng |
|---|---|---|
| Có thật, mua vé được | "Tata Show", "King's Garden" | `attraction` |
| Câu quảng cáo | "3 lý do bạn phải đến VinWonders" | `destination_highlight` |

Nếu để chung, khách hỏi *"Nha Trang có gì chơi"* thì bot có thể trả lời bằng khẩu hiệu
marketing thay vì tên show và giờ diễn.

**Vì sao `attraction.parent_id` toàn NULL.** Đã rà lại: **data không chứa quan hệ cha–con tường
minh** giữa các điểm tham quan. Cột vẫn giữ để dùng khi có dữ liệu thật, nhưng **không bịa
quan hệ để lấp nó**.

---

## 5. Sân golf

### Lưu trữ cái gì

6 sân golf và các tiện ích, trải nghiệm, bản đồ của từng sân.

### JSON gốc

```jsonc
{
  "name": "Vinpearl Golf Hai Phong",
  "location": { "destination": "Hai Phong", "island": "Vu Yen Island" },
  "general_information": {
    "designer": "IMG Worldwide",
    "number_of_holes": 36,
    "par": 72,
    "course_length": "Lake Course: 7,318 yards; Marsh Course: 7,508 yards",
    "distinctive_features": ["Golf Island in the Heart of the Port City", "..."],
    "awards_and_recognitions": []
  },
  "amenities":   [{ "name": "Restaurant",  "description": "..." }],
  "experiences": [{ "title": "F&B", "description": "...", "image_url": "..." }],
  "golf_course_maps": [{ "course_type": "Marsh Course", "map_url": "..." }]
}
```

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `golf_course` | Sân golf: số lỗ, par, người thiết kế, địa chỉ | 6 |
| `golf_feature` | Tiện ích + trải nghiệm + đặc điểm + giải thưởng + **bản đồ** | 67 |

### Vì sao chia như vậy

**Vì sao `golf_course` là bảng riêng dù chỉ 6 dòng.** Vì nó có thuộc tính mà **không thực thể
nào khác có**: `holes`, `par`, `designer`, `course_length_raw`. Nhét 6 sân vào `attraction` sẽ
thêm 6 cột NULL cho toàn bộ 78 dòng còn lại, và câu hỏi *"sân golf 18 lỗ"* không viết được.

**Vì sao gộp 5 mảng vào `golf_feature`.** `amenities`, `experiences`, `distinctive_features`,
`awards_and_recognitions` và `golf_course_maps` — năm tên khác nhau nhưng **cùng hình dạng**
`{tiêu đề, mô tả/ảnh}`, cùng thuộc về một sân, cùng là 1–N. Đủ ba điều kiện để gộp, phân biệt
bằng cột `kind`. Bản đồ dùng thêm cột `variant` để giữ `Marsh Course` / `Lake Course`.

> `course_length` được giữ nguyên dạng chuỗi vì một sân có thể có nhiều đường: *"Lake Course:
> 7,318 yards; Marsh Course: 7,508 yards"*. Tách thành số sẽ mất thông tin.

---

## 6. Hội nghị (MICE)

### Lưu trữ cái gì

Địa điểm tổ chức hội nghị, phòng họp, và sức chứa theo từng kiểu bố trí bàn ghế.

### JSON gốc

```jsonc
{
  "name": "Crystal Ballroom",
  "area": "1250m 2",
  "specifications": ["Dimensions: 50m x 25m", "Ceiling height: 7m"],
  "capacities": {
    "Theater": "1065", "Classroom": "600", "U-Shape": "120",
    "Boardroom": "160", "Banquet": "600", "Cocktail": "930"
  }
}
```

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `mice_venue` | Địa điểm: trung tâm hội nghị, nhà hát, khách sạn | 10 |
| `mice_room` | Phòng họp: diện tích, kích thước, chiều cao trần | 36 |
| `mice_room_capacity` | Sức chứa theo kiểu bố trí | 191 |

### Vì sao chia như vậy

**Vì sao `capacities` thành bảng chứ không phải JSONB.** Đây là quyết định quan trọng nhất
của miền này. `capacities` là dict có **key động**:

```
{"Theater": "1065", "Banquet": "600", ...}
```

Nếu biến mỗi key thành một cột thì thêm kiểu bố trí mới là phải chạy migration. Nếu để JSONB
thì câu hỏi thật — *"phòng nào chứa 500 khách kiểu banquet"* — không viết được bằng SQL có
index. Thành bảng thì chỉ là:

```sql
WHERE layout = 'banquet' AND pax >= 500
```

> **Cạm bẫy dữ liệu:** `area` = `"1250m 2"` — số 2 là ký tự mũ `²` bị tách ra, không phải giá
> trị. Và `"Dimensions: 22,839m x 12,938m"` thì dấu phẩy là **dấu thập phân** (22,8m × 12,9m),
> ngược hẳn với `"1,944USD"` là phân tách nghìn. Cùng khuôn mẫu, hai nghĩa trái ngược — nên
> hàm parse tiền và parse kích thước phải tách riêng.

---

## 7. Ưu đãi

### Lưu trữ cái gì

Chương trình khuyến mãi, quyền lợi, mã giảm giá, điều khoản, và toàn bộ nội dung trang.

### JSON gốc

```jsonc
{
  "promotion_id": "1b2fd7cba7c92687519ea6c3",
  "title": "Buy at a bargain price and relax in peace with Vinpearl",
  "destinations": ["Nha Trang", "Phú Quốc", "..."],
  "promotion_type": ["combo_package", "..."],
  "benefits": [{ "benefit_type": "percentage_discount", "value": 15.0,
                 "unit": "percent", "maximum": true }],
  "redemption_steps": ["With just a few simple steps...", "..."],
  "terms_and_conditions": [],
  "general_validity": { "start_date": null, "end_date": null },
  "booking_period":   { "start_date": null, "end_date": "2026-10-10" }
}
```

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `promotion` | Ưu đãi: tiêu đề, **5 loại khoảng thời gian**, điểm chất lượng | 38 |
| `promotion_benefit` | Quyền lợi: giảm bao nhiêu %, tặng gì | 310 |
| `promotion_destination` | Áp dụng ở địa danh nào | 89 |
| `promotion.tags` | Cột JSONB: 5 chiều phân loại | 561 giá trị |
| `promotion_code` | Mã giảm giá: MEMBER3, HAPPY10… | 45 |
| `promotion_section` | Nội dung văn xuôi của trang | 164 |
| `promotion_block` | Bảng biểu, danh sách, tiêu đề trong trang | 507 |
| `promotion_term` | Điều khoản + quy tắc kết hợp + liên hệ + **bước đổi thưởng** | 188 |
| `promotion_relation` | Liên kết sang ưu đãi / thương hiệu khác | 131 |
| `promotion_property_raw` | **Bảng kiểm dịch** — dữ liệu quá bẩn | 327 |

### Vì sao chia như vậy

**Vì sao 124 dòng nguồn chỉ còn 38.** Cùng một ưu đãi xuất hiện ở nhiều file (mỗi file là một
địa danh). Đã so từng cặp bản sao: **49 cặp lệch nhau, và lệch duy nhất ở trường
`destinations`**. Nên quy tắc là: giữ bản đầu tiên, **hợp** danh sách địa danh của mọi bản sao.

> Đây là giá trị lớn nhất mà database mang lại so với để nguyên file: **danh tính xuyên file**
> chỉ tồn tại khi có khoá chính.

**Vì sao 5 cặp cột ngày chứ không phải 1.** Nguồn có sẵn **5 object** khoảng thời gian với ngữ
nghĩa khác hẳn nhau:

| Object | Nghĩa | Có ngày |
|---|---|---:|
| `general_validity` | Hiệu lực chung | 32/38 |
| `booking_period` | Hạn **đặt** | 10/38 |
| `stay_period` | Hạn **lưu trú** | 7/38 |
| `purchase_period` | Hạn **mua** voucher | 2/38 |
| `redemption_period` | Hạn **dùng** voucher | 2/38 |

*"Đặt trước 30/9 để ở đến 31/12"* là hai khoảng riêng biệt. Gộp làm một là mất thông tin.

**Vì sao gộp 5 chiều phân loại vào `promotion.tags`.** `promotion_type`, `applicable_services`,
`channels`, `customer_groups`, `member_tiers` — cả 5 đều là **mảng chuỗi phẳng**, cùng cha,
cùng cách truy vấn. Tách 5 bảng gần như giống hệt nhau là ồn ào.

**Vì sao `promotion_property_raw` phải tách riêng.** Trường `applicable_properties` có 327 giá
trị nhưng **phần lớn là chuỗi cụt** do lỗi parse:

```
"Vinwonders Wave Park &"
"Vinwonders Phu Quoc |"
"Vinwonders Nha Trang –"
```

Ép khoá ngoại vào `property` sẽ làm **hỏng cả lần nạp**. Nên để riêng một bảng kiểm dịch, khớp
mờ bằng `pg_trgm` sau khi có thời gian.

**Vì sao không tin `promotion_status`.** Trường này được crawler tính lúc `2026-08-01` — cũ ngay
khi nạp vào. Lược đồ hạ nó xuống thành `status_at_crawl` chỉ để tham chiếu; trạng thái thật
lấy từ view `promotion_active` tính theo `CURRENT_DATE`.

---

## 8. Tri thức: FAQ, chính sách, giới thiệu

### Lưu trữ cái gì

Câu hỏi thường gặp, văn bản điều khoản, và thông tin công ty.

### JSON gốc

```jsonc
// faqs/vinpearl_faqs.json — CÓ HAI BẢN của cùng 174 mục
"items": [{ "category": "Hotels", "subcategory": "Accommodation",
            "question": "Where are Vinpearl's properties?", "answer": "..." }],
"items_by_category": { "Hotels": [ ...y hệt... ] }

// regulations/vinpearl_regulations.json
"documents": [{
  "id": "ab8c79e6ba880330", "title": "General Terms", "category": "general_terms",
  "plain_text": "...39.061 ký tự...",
  "sections": [{ "heading": "General content", "content": ["...", "..."] }],
  "tables":   [{ "headers": [], "rows": [[...]] }],
  "lists":    [{ "type": "ol", "items": [...] }]
}]
```

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `faq` | Câu hỏi và trả lời, phân theo nhóm | 171 |
| `policy_document` | Văn bản: điều khoản, chính sách bảo mật | 7 |
| `policy_section` | Từng mục có tiêu đề trong văn bản | 36 |
| `policy_block` | Bảng biểu và danh sách trong văn bản | 15 |
| `org_info` | Thông tin pháp nhân — **đúng một dòng** | 1 |
| `org_highlight` | Mục nổi bật trên trang giới thiệu | 14 |

### Vì sao chia như vậy

**Vì sao chỉ lấy `items[]`, bỏ `items_by_category{}`.** Hai trường này chứa **y hệt** cùng 174
mục, chỉ khác cách nhóm. Nhóm theo category là việc của câu `GROUP BY`, không phải việc của
lưu trữ.

**Vì sao FAQ ra 171 chứ không phải 174.** Nguồn có **3 câu hỏi lặp y hệt**. Khoá chính là hash
của câu hỏi nên chúng tự gộp. Việc này được ghi lại thành `data_quality_issue` để không ai
tưởng pipeline làm mất dòng.

**Vì sao tách `policy_section` khỏi `policy_document`.** Vì lớp RAG sau này sẽ chunk **theo
từng mục có tiêu đề**, chứ không cắt mù mỗi 1.800 ký tự giữa câu như cách làm hiện tại.

**Vì sao gộp `tables` và `lists` thành `policy_block`.** Cả hai đều là "khối có cấu trúc",
hiếm khi truy vấn riêng lẻ, và payload để JSONB là đủ.

**Vì sao `org_info` chỉ một dòng.** Nó là thông tin công ty — có đúng một Vinpearl. Ràng buộc
`CHECK (id = 1)` đảm bảo không ai vô tình chèn dòng thứ hai.

---

## 9. Ứng dụng: người dùng và hội thoại

### Lưu trữ cái gì

Người dùng, phiên chat, từng tin nhắn, nguồn bot đã dùng, và ticket chuyển người thật.

### JSON gốc

**Không có.** Miền này không đến từ `data/`, nó suy từ code hiện có:
`src/backend/api/routes.py`, `src/backend/agents/state.py`.

### Các bảng

| Bảng | Lưu gì |
|---|---|
| `app_user` | Người dùng. Chưa đăng nhập **vẫn có một dòng** |
| `session` | Phiên trò chuyện, id do client sinh |
| `message` | Từng tin nhắn — **nơi duy nhất lưu nội dung thô** |
| `message_citation` | Bot đã dùng nguồn nào để trả lời |
| `message_feedback` | Đánh giá tốt / xấu |
| `ticket` | Yêu cầu chuyển cho người thật |
| `event_log` | Nhật ký vận hành |

### Vì sao chia như vậy

**Vì sao người chưa đăng nhập vẫn có dòng `app_user`.** Chatbot tra cứu du lịch không có lý do
bắt đăng nhập. Nhưng vẫn cần định danh để nối các phiên lại. Khi nào cần tài khoản thật thì
chỉ việc điền `email` + `password_hash` vào đúng dòng đó — **lịch sử chat không mất**.

**Vì sao `message_citation` đáng giá nhất nhóm này.** Hiện `routes.py` dựng danh sách nguồn rồi
**vứt đi**. Giữ lại thì:

- Trả lời sai → truy ngược được đúng nguồn nào gây ra
- Đo được recall thật, không phải đoán
- Biết nguồn nào không bao giờ được dùng → dữ liệu thừa, cắt bớt

**Vì sao nội dung thô chỉ nằm ở `message`.** Khách sẽ gõ số điện thoại, mã đặt phòng vào ô
chat. Gom về một chỗ thì chính sách xoá và lưu trữ chỉ phải áp một nơi. `event_log` cố ý
**không** lưu nội dung, chỉ lưu độ dài và hash.

---

## 10. Vận hành và chất lượng dữ liệu

### Lưu trữ cái gì

Nhật ký mỗi lần nạp, và mọi chỗ dữ liệu nguồn bị lỗi.

### Các bảng

| Bảng | Lưu gì | Dòng |
|---|---|---:|
| `ingest_run` | Mỗi lần chạy `load_core` là một dòng | 9 |
| `data_quality_issue` | Mọi thứ không parse được, kèm vị trí chính xác | 1.831 |

### Vì sao chia như vậy

**Vì sao cần `data_quality_issue`.** Nguyên tắc: **không bao giờ `except: pass`**. Mỗi chỗ dữ
liệu hỏng đều được ghi lại kèm `json_path` trỏ đúng vị trí trong file nguồn:

```
rule       = "rate.not_a_price"
json_path  = "hotels[3].rooms[7].standard_rate"
raw_value  = "tel:1900232389"
```

Không dòng nào biến mất trong im lặng.

**Vì sao `ingest_run` ghi bằng kết nối riêng.** Nếu dùng chung một giao dịch với phần nạp dữ
liệu, thì lần nạp thất bại sẽ rollback luôn cả nhật ký lỗi — mất đúng thứ cần để biết vì sao
nó hỏng.

---

# Phần C — Gộp bảng: so sánh công tâm

## C.1 Lược đồ đã gộp 9 chỗ

Ánh xạ 1–1 từ cấu trúc JSON sẽ ra khoảng **60 bảng**. Lược đồ hiện tại còn **43**.

| Bảng | Gộp từ | Bớt |
|---|---|---:|
| `attraction` | 7 loại điểm tham quan | −6 |
| `promotion.tags` | 5 chiều phân loại | −4 |
| `golf_feature` | 4 mảng của sân golf | −3 |
| `promotion_term` | 3 mảng điều khoản | −2 |
| `promotion_block` | bảng + danh sách + tiêu đề | −2 |
| `policy_block` | bảng + danh sách | −1 |

Và ba lần gộp cùng-hình-dạng, đưa 48 xuống 45:

| Gộp | Kết quả | Bớt |
|---|---|---:|
| `promotion_step` → `promotion_term` (`kind='step'`) | 110 → **188 dòng** | −1 |
| `golf_course_map` → `golf_feature` (`kind='map'`) | 61 → **67 dòng** | −1 |
| `attraction_itinerary_day` → cột `attraction.itinerary` | 7 ngày trong **3 dòng JSONB** | −1 |

Và hai lần gộp bảng-nối thành cột, đưa 45 xuống 43:

| Gộp | Kết quả | Bớt |
|---|---|---:|
| `room_amenity` → `room.amenity_ids TEXT[]` | 1.796 dòng thành **cột mảng** | −1 |
| `promotion_tag` → `promotion.tags JSONB` | 561 dòng thành **cột JSONB** | −1 |

Hai lần này **khác về bản chất** với ba lần trên: chúng đánh đổi ràng buộc lấy số
bảng. Postgres không có khoá ngoại cho phần tử mảng, JSONB không có CHECK theo khoá.
Bù lại truy vấn còn gọn hơn — một điều kiện mảng thay cho cả một JOIN.

**Một lần gộp nữa đã làm rồi tách lại.** Bốn bảng `*_section` / `*_block` từng thành
hai bảng đa hình `content_section` / `content_block`. Đã bỏ: đa hình chỉ hoà vốn khi
có nhiều loại chủ sở hữu — `media` có 8 nên đáng, bốn bảng kia chỉ có 2 nên không.
Xem C.4.

## C.2 Ba phương án — so sánh thẳng thắn

Có ba hướng đi. Tôi trình bày **ưu điểm thật** của cả ba, không thiên vị.

### Phương án 1 — Gộp tối đa (~20 bảng)

Gộp mọi thứ cùng "chủ đề" vào một bảng, phân biệt bằng cột `kind`. Ví dụ một bảng `place` gồm
khách sạn + sân golf + địa điểm hội nghị; một bảng `content` gồm FAQ + chính sách + điểm tham
quan.

**Ưu điểm — có thật, không nên bỏ qua:**

- Ít bảng để nhớ, người mới nhìn vào bớt choáng
- Viết ít `JOIN` hơn, câu truy vấn ngắn hơn
- Thêm một loại địa điểm mới chỉ cần thêm giá trị `kind`, **không cần migration**
- File model ngắn hơn nhiều

**Nhược điểm:**

- Cột `holes`, `par` chỉ có nghĩa với golf → **NULL ở 90% số dòng**
- **Không đặt được `NOT NULL`** cho cột nào, vì mỗi `kind` cần cột khác nhau
- **Không đặt được `CHECK` có nghĩa** — `par` phải 70–73 với golf nhưng vô nghĩa với khách sạn
- Mọi câu truy vấn phải nhớ thêm `WHERE kind = '...'`, quên là ra kết quả sai

### Phương án 2 — Gộp như đã làm (43 bảng)

Chỉ gộp những chỗ **cùng hình dạng, cùng cha, cùng lực lượng**:

| Gộp | Vì sao an toàn |
|---|---|
| `promotion_step` → `promotion_term` | Cùng `(promotion_id, ord, text)`. Chỉ thêm `kind='step'` |
| `golf_course_map` → `golf_feature` | Bản đồ cũng là `{tên, ảnh}` của một sân |
| `attraction_itinerary_day` → cột JSONB | 7 dòng, không ai truy vấn riêng một ngày |

**Ưu điểm:**

- Giữ được toàn bộ ràng buộc `NOT NULL` và `CHECK`
- Sửa một chỗ thiếu nhất quán có thật (`promotion_step` lẽ ra đã phải nằm trong `promotion_term`)
- Không phải viết lại adapter hay migration lớn

**Nhược điểm — thừa nhận sòng phẳng:**

- Vẫn 43 bảng, người mới vẫn phải làm quen
- Vẫn phải `JOIN` nhiều

### Phương án 3 — Dừng ở 48 bảng (trạng thái ban đầu)

**Ưu điểm:** không mất công, không rủi ro.
**Nhược điểm:** để lại một chỗ thiếu nhất quán rõ ràng mà ai đọc kỹ cũng nhận ra.

## C.3 So sánh cạnh nhau

| Tiêu chí | Gộp tối đa (~20) | **Đã làm (43)** | Không gộp (48) |
|---|---|---|---|
| Số bảng phải nhớ | Ít nhất | Trung bình | Nhiều nhất |
| Số `JOIN` khi truy vấn | Ít nhất | Trung bình | Trung bình |
| Ràng buộc `NOT NULL` | **Gần như mất hết** | Đầy đủ | Đầy đủ |
| Ràng buộc `CHECK` | **Gần như mất hết** | Đầy đủ | Đầy đủ |
| Cột NULL vô nghĩa | Rất nhiều | Không | Không |
| Rủi ro quên `WHERE kind` | **Cao** | Thấp | Thấp |
| Đếm số thực thể | Phải `DISTINCT` | `COUNT(*)` | `COUNT(*)` |
| Công sức thực hiện | Lớn, viết lại nhiều | Đã xong | Không |

## C.4 Vì sao dừng ở phương án 2

Điểm quyết định **không phải** số bảng, mà là **ràng buộc**.

Lược đồ này làm việc với dữ liệu bẩn có hệ thống. Chính các ràng buộc đã bắt được **3 lỗi thật**
ngay lần nạp đầu tiên:

| Ràng buộc | Bắt được gì |
|---|---|
| `NUMERIC(6,2)` tràn số | Phòng hội nghị "rộng 22 km" do đọc sai dấu thập phân |
| `CHAR(2)` quá dài | Mã ngôn ngữ `"en-US"` — 29 dòng bị từ chối |
| Khoá ngoại | Sức chứa trỏ tới phòng không tồn tại |

Nếu gộp tối đa, **cả ba ràng buộc này đều không đặt được**, và ba lỗi trên sẽ lặng lẽ đi vào
database. Nói cách khác: gộp quá tay là **tự tháo bỏ lưới an toàn** của chính mình để đổi lấy
việc viết ít `JOIN` hơn.

Còn một lý do nữa, ít kỹ thuật hơn nhưng thật: cái làm lược đồ dễ quản lý không phải số bảng,
mà là **tên có tiền tố theo miền** (`promotion_*`, `golf_*`, `mice_*`, `policy_*`) và **nhóm
lại**. 43 bảng chia 8 nhóm là ~5 bảng mỗi nhóm — con số não người xử lý được. Một bảng 25 cột
mà mỗi `kind` chỉ dùng 8 cột thì khó đọc hơn hai bảng 10 cột rõ ràng.

## C.5 Hai chỗ tách vì nghiệp vụ, đừng gộp

Cuối cùng, có hai bảng **về mặt kỹ thuật thì gộp được**, nhưng gộp là xoá bỏ một quyết định đã
cân nhắc:

| Bảng | Kỹ thuật | Nhưng |
|---|---|---|
| `destination_highlight` (28) | Có thể là `attraction` với `kind='highlight'` | Tách để bot tìm kiếm **không bao giờ** nhầm câu quảng cáo thành hoạt động có thật |
| `promotion_property_raw` (327) | Có thể là cột trong `promotion` | Tách vì dữ liệu quá bẩn — ép khoá ngoại sẽ làm hỏng cả lần nạp |

## C.6 Kết luận

| Phương án | Số bảng | Đánh giá |
|---|---:|---|
| Ánh xạ 1–1 từ JSON | ~60 | Quá vụn |
| Gộp tối đa | ~20 | Mất ràng buộc, đổi an toàn lấy tiện tay |
| **Hiện tại** | **43** | Giữ ràng buộc ở chỗ quan trọng, gộp ở chỗ rẻ |

Ba lần gộp cùng-hình-dạng **an toàn tuyệt đối**: không mất ràng buộc nào, không sinh cột
NULL nào. Bốn lần gộp bảng-nối **có trả giá** và cái giá đã biết trước (xem C.4). Tất cả
đã áp dụng và kiểm chứng bằng 132 test.

## C.4 Bốn chỗ đã cân nhắc gộp nhưng quyết định giữ

**Phép thử cho bảng đa hình: đếm số loại chủ sở hữu.** Đa hình trả giá bằng ràng
buộc (mất khoá ngoại, mất CASCADE, DataGrip không vẽ được đường nối), và cái giá đó
**cố định** dù có 2 hay 20 loại chủ. Lợi ích thì tỉ lệ với số loại chủ.

| Bảng | Dòng | Vì sao giữ |
|---|---:|---|
| `*_section` + `*_block` (4 bảng) | 722 | Đã thử gộp thành 2 bảng đa hình rồi tách lại. Chỉ 2 loại chủ sở hữu — không đủ hoà vốn cho cái giá mất khoá ngoại |
| `mice_room_capacity` | 191 | Câu hỏi thật là *"phòng nào chứa 300 người kiểu rạp hát"* → `WHERE layout=? AND pax>=?` chạy thẳng trên index. Thành JSONB phải cần 6 index biểu thức cho 6 kiểu bố trí — đổi 1 bảng lấy 6 index là lỗ |
| `destination_alias` | 32 | Có `UNIQUE(alias_normalized)` **toàn cục**: một bí danh không được trỏ về hai địa danh. Mảng không giữ được ràng buộc này, mà đây lại là đường vào duy nhất để tra địa danh |
| `promotion_destination` | 89 | Chính là join phục vụ câu hỏi số một của bot: *"ưu đãi nào ở Phú Quốc"*. Giữ khoá ngoại |

## C.5 Cách rẻ hơn: schema và view

Số bảng không phải thứ duy nhất quyết định "dễ quản lý".

**Tách schema** — 41 bảng chia `core` (34) và `app` (7). DataGrip hiện hai thư mục gập
được thay vì danh sách phẳng. Một migration, không đụng dữ liệu, không mất ràng buộc.

**Dựng view** — 11 view trong schema `api`: `api.hotel` trả về khách sạn kèm phòng và
nhà hàng dạng JSON; `api.room` tra sẵn tên tiện nghi từ mảng id; `api.promotion` gộp
địa danh, nhãn, quyền lợi, mã và điều khoản. Code đọc thấy 11 view thay vì 34 bảng.

Quy tắc: **`core.*` là bảng thật, `api.*` là cùng thứ đó đã gộp sẵn.** Đổi tiền tố
schema là chuyển qua lại giữa hai dạng.
