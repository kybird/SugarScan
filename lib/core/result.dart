/// 성공/실패를 명시적으로 표현하는 최소 Result 타입.
///
/// 예외 대신 이 타입을 쓰는 이유: OCR·동기화 경로에서는 "실패가 정상 흐름"이라
/// 호출부가 실패를 처리했는지 컴파일 타임에 드러나야 한다.
sealed class Result<T, E> {
  const Result();

  const factory Result.ok(T value) = Ok<T, E>;
  const factory Result.err(E error) = Err<T, E>;

  bool get isOk => this is Ok<T, E>;
  bool get isErr => this is Err<T, E>;

  T? get valueOrNull => switch (this) {
        Ok(:final value) => value,
        Err() => null,
      };

  E? get errorOrNull => switch (this) {
        Ok() => null,
        Err(:final error) => error,
      };

  R fold<R>(R Function(T value) onOk, R Function(E error) onErr) =>
      switch (this) {
        Ok(:final value) => onOk(value),
        Err(:final error) => onErr(error),
      };
}

final class Ok<T, E> extends Result<T, E> {
  const Ok(this.value);
  final T value;

  @override
  String toString() => 'Ok($value)';
}

final class Err<T, E> extends Result<T, E> {
  const Err(this.error);
  final E error;

  @override
  String toString() => 'Err($error)';
}
