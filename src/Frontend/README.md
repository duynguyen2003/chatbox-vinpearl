# Tong quan Frontend

Frontend cua du an la ung dung React chay bang Vite. Ma nguon FE nam chu yeu trong thu muc `src/Frontend`, con diem khoi dong React nam o `src/main.jsx` va `src/App.jsx`.

Ung dung dang mo phong website dat phong/nghi duong VinTravel, gom cac chuc nang chinh:

- Trang chu hien thi hero search, diem den, resort noi bat va combo uu dai.
- Trang tim kiem resort co bo loc theo diem den, loai hinh va gia toi da.
- Trang chi tiet resort co gallery anh, danh sach phong, tien ich va chinh sach.
- Chatbot AI Concierge, goi API backend neu co, fallback sang cau tra loi local neu backend loi.
- Trang tao support ticket, goi API backend neu co, fallback sang ticket local.
- Dang nhap/dang ky gia lap bang React Context.
- Doi ngon ngu EN/VI, trong do KO/ZH hien dang fallback ve EN.

## Cach chay Frontend

Neu chay truc tiep bang Node:

```bash
npm install
npm run dev
```

Sau do mo URL Vite hien tren terminal, thuong la:

```text
http://localhost:5173
```

Neu muon ben backend clone code ve va chay FE bang Docker Compose thi may host chi can Docker, khong can cai Node. Tuy nhien `docker-compose.yml` hien tai cua project moi co service `backend`, chua co service `frontend`. Can them service FE rieng neu muon compose dung ca BE va FE.

Vi du service FE co the them vao compose:

```yaml
frontend:
  image: node:20
  working_dir: /app
  volumes:
    - ./:/app
  command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
  ports:
    - "5173:5173"
  depends_on:
    - backend
```

## Luong khoi dong ung dung

### `src/main.jsx`

Day la entry point cua React. File nay:

- Import `StrictMode` tu React.
- Import `createRoot` tu `react-dom/client`.
- Import CSS global tu `src/index.css`.
- Render component `App` vao DOM element co id la `root` trong `index.html`.

### `src/App.jsx`

Day la component goc cua ung dung. File nay boc toan bo app bang:

- `BrowserRouter`: bat routing theo URL tren browser.
- `LanguageProvider`: cung cap ngon ngu hien tai va object text `t`.
- `AuthProvider`: cung cap thong tin user, ham login/logout.
- `AppRoutes`: noi khai bao tat ca route/page.

`div translate="no" className="notranslate"` dung de han che browser/extension tu dong dich noi dung UI.

## Cau truc thu muc FE

```text
src/Frontend/
  components/       Component tai su dung tren nhieu page
  context/          React Context cho auth va ngon ngu
  data/             Du lieu mock local
  pages/            Cac man hinh chinh theo route
  routes/           Cau hinh route va layout chung
  services/         Lop goi API/fallback data
  styles/           CSS tach theo component, page va route
```

## Routes

### `routes/AppRoutes.jsx`

File nay khai bao ban do URL cua ung dung:

- `/`: trang chu `Home`.
- `/search`: trang ket qua tim kiem `SearchResults`.
- `/hotels/:hotelId`: trang chi tiet resort `HotelDetail`.
- `/chat` va `/chatbot`: trang chatbot `Chatbot`.
- `/support`: trang support ticket `Ticket`.
- `/login`: trang dang nhap `Login`.
- `/register`: trang dang ky `Register`.
- `*`: route khong ton tai se redirect ve `/`.

Trong file nay co `AppLayout`, la layout chung cho cac page noi dung. Layout gom:

- `Header`
- `main`
- `Footer`
- `ChatWidget`

Hai page `Login` va `Register` khong dung `AppLayout`, vi day la man hinh auth rieng.

## Context

### `context/AuthContext.jsx`

Quan ly trang thai dang nhap gia lap.

Noi dung chinh:

- `user`: state luu user hien tai. Mac dinh dang co san user `Victoria Tran`.
- `login(email, name)`: tao user moi tu email/name va set vao state.
- `logout()`: set user ve `null`.
- `useAuth()`: custom hook de component lay `user`, `login`, `logout`.

Day chua phai authentication that voi backend. Password trong login/register hien chi dung de submit form, khong duoc gui len API.

### `context/LanguageContext.jsx`

Quan ly ngon ngu va text hien thi.

Noi dung chinh:

- `EN`: bo text tieng Anh.
- `VI`: bo text tieng Viet, ke thua `EN` va override cac key can dich.
- `TRANSLATIONS`: map ngon ngu `EN`, `VI`, `KO`, `ZH`.
- `language`: state ngon ngu hien tai, mac dinh la `EN`.
- `setLanguage`: doi ngon ngu.
- `t`: object text theo ngon ngu hien tai.
- `useLanguage()`: custom hook de cac component lay `language`, `setLanguage`, `t`.

Hien tai `KO` va `ZH` dang tro ve `EN`, nen neu chon Korean/Chinese thi UI van hien text English.

## Data

### `data/mockData.js`

Chua du lieu local dung khi backend chua san sang hoac API loi.

File nay export:

- `DESTINATIONS`: danh sach diem den nhu Phu Quoc, Nha Trang, Hoi An, Ha Long.
- `HOTELS`: danh sach resort/hotel, gom id, ten, diem den, gia, rating, anh, tien ich, mo ta, chinh sach va cac loai phong.
- `COMBOS`: cac goi uu dai/combo du lich hien tren trang chu.

Nhieu page va component doc data tu file nay de render UI.

## Services

### `services/api.js`

Day la lop giao tiep voi backend. File nay co chien luoc: thu goi API truoc, neu API loi thi fallback ve du lieu local.

Ham chinh:

- `fetchHotels(filters)`: goi `/api/hotels` voi query `destination`, `type`, `maxPrice`. Neu fail thi loc `HOTELS` tren client.
- `fetchHotelById(id)`: goi `/api/hotels/:id`. Neu fail thi tim hotel trong `HOTELS`.
- `sendChatMessage(prompt, language, history)`: POST `/api/chat`. Neu fail thi tao cau tra loi local bang `generateFallbackResponse`.
- `submitSupportTicket(ticketData)`: POST `/api/tickets`. Neu fail thi tao ticket local voi id dang `TK-xxxx`.
- `fetchTickets()`: GET `/api/tickets`. Neu fail thi tra ve mot ticket mau.

Voi Vite dev server, cac URL dang la relative path nhu `/api/chat`. Muon proxy sang backend port `8000` thi nen cau hinh proxy trong `vite.config.js`, hoac dam bao FE/BE cung domain khi deploy.

## Pages

### `pages/Home.jsx`

Trang chu cua website.

Noi dung chinh:

- Render `HeroSearch`.
- Render danh sach `DESTINATIONS` bang `DestinationCard`.
- Render banner AI Concierge, link sang `/chat` va `/support`.
- Render cac hotel co `featured: true` bang `HotelCard`.
- Render danh sach combo tu `COMBOS`.
- Co `VI_COMBO_COPY` de override noi dung combo khi ngon ngu la VI.

### `pages/SearchResults.jsx`

Trang ket qua tim kiem resort.

Noi dung chinh:

- Doc query params bang `useSearchParams`.
- Quan ly filter: `destFilter`, `typeFilter`, `maxPrice`.
- Goi `fetchHotels()` moi khi filter thay doi.
- Hien skeleton khi loading.
- Hien grid `HotelCard` khi co ket qua.
- Hien empty state va nut sang chatbot khi khong co ket qua.
- Dung `FilterSidebar` de nguoi dung dieu chinh bo loc.

### `pages/HotelDetail.jsx`

Trang chi tiet mot resort.

Noi dung chinh:

- Lay `hotelId` tu URL `/hotels/:hotelId`.
- Goi `fetchHotelById()` de lay du lieu.
- Hien gallery anh va thumbnail.
- Co tab `rooms`, `overview`, `policies`.
- Nut chon phong tao toast dat phong gia lap.
- Nut lap lich trinh voi AI dieu huong sang `/chat?prompt=...`.

### `pages/Chatbot.jsx`

Trang chat day du voi AI Concierge.

Noi dung chinh:

- Lay `prompt` tu query string neu page duoc mo tu nut "Ask AI".
- Luu danh sach message trong state.
- Goi `sendChatMessage()` khi user gui prompt.
- Auto scroll xuong message moi.
- Co suggested prompts.
- Neu response co `relatedHotels`, render them cac `HotelCard`.
- Co nut reset conversation va link sang support ticket.

### `pages/Ticket.jsx`

Trang tao va xem support ticket.

Noi dung chinh:

- Form gom ten, email, phone, ngon ngu, subject, noi dung.
- Goi `submitSupportTicket()` khi submit.
- Goi `fetchTickets()` khi page mount de lay lich su ticket.
- Hien success message sau khi submit.
- Hien badge trang thai `Resolved`, `Processing`, hoac `Pending`.

### `pages/Login.jsx`

Trang dang nhap gia lap.

Noi dung chinh:

- Form email/password.
- Khi submit, neu co email thi goi `login(email)`.
- Sau login dieu huong ve `/`.
- Link sang trang register.

### `pages/Register.jsx`

Trang dang ky gia lap.

Noi dung chinh:

- Form name/email/password.
- Khi submit, neu co email thi goi `login(email, name)`.
- Sau register dieu huong ve `/`.
- Link sang trang login.

## Components

### `components/Header.jsx`

Header chung cua app.

Noi dung chinh:

- Logo Vinpearl.
- Navigation toi `/search`, `/`, `/chat`, `/support`.
- Dropdown doi ngon ngu desktop.
- Nut doi ngon ngu nhanh tren mobile.
- Hien user/avatar/logout neu dang dang nhap.
- Hien link sign in neu `user` la `null`.
- Mobile drawer khi bam icon menu.

### `components/Footer.jsx`

Footer chung cua app. Thuong hien mo ta brand, cac diem den, dich vu AI, thong tin lien he va link phu.

### `components/HeroSearch.jsx`

Khu hero search tren trang chu.

Noi dung chinh:

- Form chon destination, check-in, check-out, guests.
- Khi submit, dieu huong sang `/search` kem query params.
- Nut "Ask AI" tao prompt tu destination/guests/budget va dieu huong sang `/chat`.
- Hien metrics nhu so resort, rating, AI support.

### `components/DestinationCard.jsx`

Card hien thi mot diem den trong `DESTINATIONS`.

Vai tro:

- Hien anh, ten, mo ta, so luong property.
- Thuong link/dieu huong sang trang search theo destination.

### `components/HotelCard.jsx`

Card hien thi tom tat mot hotel/resort.

Vai tro:

- Hien anh, ten, vi tri, rating, gia, loai hinh va tien ich ngan.
- Link sang trang chi tiet `/hotels/:hotelId`.
- Co the duoc tai su dung o trang chu, search va chatbot.

### `components/FilterSidebar.jsx`

Sidebar bo loc trong trang search.

Vai tro:

- Chon destination.
- Chon property type.
- Dieu chinh max price.
- Reset filter.
- Tra state filter ve `SearchResults` thong qua props setter.

### `components/ChatWidget.jsx`

Widget chat nho hien chung trong layout.

Vai tro:

- Cho user mo nhanh AI Concierge tu bat ky page nao dung `AppLayout`.
- Co input/suggestion ngan.
- Co link mo workspace chat day du.

## Styles

CSS duoc tach theo dung noi su dung:

```text
styles/components/  CSS cho component tai su dung
styles/pages/       CSS cho tung page
styles/routes/      CSS cho layout/routing
```

Vi du:

- `styles/components/Header.css` style cho `Header.jsx`.
- `styles/pages/Home.css` style cho `Home.jsx`.
- `styles/routes/AppRoutes.css` style cho layout chua header/main/footer/widget.

CSS global cua toan app nam o `src/index.css`, gom bien mau, reset co ban, style chung cho body, link, button/input/select/textarea va mot so utility class.

## Luu y khi ket noi Backend

Frontend hien goi API bang relative URL:

```text
/api/hotels
/api/hotels/:id
/api/chat
/api/tickets
```

Neu chay FE o `localhost:5173` va BE o `localhost:8000`, can mot trong cac cach sau:

- Them proxy trong `vite.config.js` de `/api` proxy sang `http://localhost:8000`.
- Doi service API de dung base URL tu environment variable.
- Deploy FE va BE cung domain/reverse proxy de `/api` tro ve backend.

Vi `api.js` da co fallback local data, FE van hien duoc giao dien co ban ngay ca khi backend chua chay. Tuy nhien cac chuc nang that nhu chat AI, ticket persistence, authentication that can backend xu ly rieng.
