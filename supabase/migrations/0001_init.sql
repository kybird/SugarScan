-- SugarScan 초기 스키마.
--
-- 이 파일은 Drift 스키마(lib/data/local/tables.dart)의 복제본이 아니다.
-- 서버에는 **의도적으로 빠진 열이 있다**:
--   - ocr_raw_text : OCR 원문. 오인식 분석용 로컬 자료라 올리지 않는다.
--   - photo_path   : 로컬 파일 경로. 사진 자체를 업로드하지 않으므로 의미가 없다.
--   - adjusted_by_user : 엔진 품질 지표. 서버 계정에 붙일 이유가 없다.
-- 수집 최소화 원칙(§10)이고, 빼는 쪽이 기본값이다. 나중에 필요해지면 열을
-- 추가하는 마이그레이션은 쉽지만, 이미 올라간 원문을 지우는 일은 어렵다.
--
-- enum 값은 Dart 쪽 `wireName` 과 문자 그대로 일치해야 한다. Dart enum 식별자
-- (preMeal)가 아니라 wireName(pre_meal)이 정본이다.

create type glucose_unit as enum ('mgdl', 'mmoll');

create type measurement_tag as enum (
  'fasting', 'pre_meal', 'post_meal', 'post_exercise', 'bedtime', 'random'
);

create type reading_source as enum (
  'ocr', 'manual', 'ble', 'health_sync', 'import'
);

create table public.glucose_readings (
  -- 서버가 아니라 클라이언트가 만드는 uuid v4. 오프라인에서 남긴 기록도
  -- 네트워크 왕복 없이 정체성을 가진다. 동기화 설계 전체가 이 전제 위에 있다.
  id                  uuid primary key,
  user_id             uuid not null references auth.users(id) on delete cascade,

  measured_at         timestamptz not null,
  tz_name             text not null,
  utc_offset_minutes  int  not null,

  -- 저장 정본. 통계·헬스 연동이 전부 이 값을 쓴다.
  value_mgdl          numeric(6,2) not null check (value_mgdl between 10 and 900),

  -- 사용자가 실제로 입력한 원본. mmol/L 로 7.6 을 넣은 사람에게 왕복 변환
  -- 결과인 7.5 를 되돌려주지 않기 위해 함께 남긴다.
  entered_unit        glucose_unit not null,
  entered_value       numeric(8,3) not null,

  tag                 measurement_tag not null default 'random',
  source              reading_source  not null default 'ocr',

  ocr_engine_id       text,
  ocr_confidence      real,
  note                text,

  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),

  -- 소프트 삭제. 다른 기기에 삭제를 전달하기 위한 것일 뿐이며,
  -- 계정 탈퇴 시에는 hard delete 한다.
  deleted_at          timestamptz
);

alter table public.glucose_readings enable row level security;

-- 혈당 기록은 전부 개인 데이터다. 공유 경로가 생기기 전까지 정책은 이 하나면 된다.
create policy "owner_all" on public.glucose_readings
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create index glucose_readings_user_measured_idx
  on public.glucose_readings (user_id, measured_at desc);

-- 델타 pull 전용. 커서(lastPulledAt)보다 큰 updated_at 만 훑는다.
create index glucose_readings_user_updated_idx
  on public.glucose_readings (user_id, updated_at);

-- updated_at 은 **서버가 찍는다.**
--
-- 클라이언트 시계는 틀어져 있을 수 있고, 델타 pull 커서가 이 값 위에 서 있다.
-- 앱이 보낸 미래 시각이 그대로 저장되면 그 뒤의 정상 변경들이 커서에 걸리지
-- 않고 통째로 유실된다. 그래서 upsert 가 무엇을 보내든 덮어쓴다.
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger glucose_readings_touch_updated_at
  before insert or update on public.glucose_readings
  for each row execute function public.touch_updated_at();
