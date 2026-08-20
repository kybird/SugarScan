# sugarScan

일반 혈당계(SMBG) LCD를 카메라로 읽어 기록하는 Flutter 앱.
인식은 **단말에서만** 돈다. 설계와 구현 이력은 [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## 실행

```bash
flutter pub get
flutter run
```

접속 정보 없이 그대로 실행된다. 서버 없이도 스캔·저장·조회가 전부 동작한다 —
로컬 SQLite(Drift)가 정본이고 Supabase 는 복제본이다.

## Supabase 연결

접속 정보는 저장소에 넣지 않고 빌드할 때 주입한다.

1. Supabase 대시보드 → **Settings → API** 에서 Project URL 과
   publishable(anon) key 를 복사한다. `service_role` 키는 절대 쓰지 않는다 —
   RLS 를 통째로 우회하며, 앱이 시작할 때 이 키를 감지하면 거부한다.
2. 스키마를 올린다. `supabase/migrations/0001_init.sql` 을 SQL Editor 에 붙여넣거나:

```bash
supabase db push
```

3. Google 로그인을 설정한다(아래 별도 절).
4. 값을 주입해 실행한다.

```bash
flutter run --dart-define=SUPABASE_URL=https://xxxx.supabase.co --dart-define=SUPABASE_PUBLISHABLE_KEY=sb_publishable_xxxx
```

매번 치기 번거로우면 `supabase.local.json` (gitignore 됨) 에 넣고:

```bash
flutter run --dart-define-from-file=supabase.local.json
```

```json
{
  "SUPABASE_URL": "https://xxxx.supabase.co",
  "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_xxxx",
  "GOOGLE_SERVER_CLIENT_ID": "xxxx-web.apps.googleusercontent.com",
  "GOOGLE_IOS_CLIENT_ID": "xxxx-ios.apps.googleusercontent.com"
}
```

예전 이름인 `SUPABASE_ANON_KEY` 도 그대로 받는다.

## Google 로그인

인증은 Google 하나만 지원한다. 익명 로그인은 쓰지 않는다 — 로그인 전 상태는
완전 로컬이고, 로그인하는 순간 그때까지 쌓인 기록이 전부 올라간다.

**Google Cloud 콘솔** → APIs & Services → Credentials 에서 OAuth 클라이언트 ID 를
만든다.

| 유형 | 필요한 값 | 쓰이는 곳 |
|---|---|---|
| 웹 애플리케이션 | 클라이언트 ID + 시크릿 | `GOOGLE_SERVER_CLIENT_ID`, Supabase 프로바이더 |
| Android | 패키지명 + SHA-1 | 등록만 (앱에 넣지 않는다) |
| iOS | 번들 ID | `GOOGLE_IOS_CLIENT_ID` |

Android 등록에 쓸 값:

- 패키지명 `com.sugarscan.sugarscan`
- 디버그 SHA-1 은 아래로 확인한다. 릴리스 빌드는 릴리스 키스토어의 SHA-1 도
  따로 등록해야 한다.

```bash
keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android
```

**Supabase 대시보드** → Authentication → Sign In / Providers → Google 을 켜고
**웹** 클라이언트 ID 와 시크릿을 넣는다. iOS/Android 클라이언트 ID 는 같은 화면의
Authorized Client IDs 에 추가한다.

> 함정: `GOOGLE_SERVER_CLIENT_ID` 에는 반드시 **웹 애플리케이션** 유형 ID 를
> 넣는다. Android 유형 ID 를 넣으면 토큰은 발급되는데 Supabase 가 거부하고,
> 오류 메시지만으로는 원인을 알기 어렵다.

## 개발

```bash
flutter analyze     # 무경고가 기본
flutter test
```

리포지토리 규약과 함정은 [`CLAUDE.md`](CLAUDE.md) 참조.
