# ─── Stage 1: builder ────────────────────────────────────────────────────────
FROM golang:1.22-alpine AS builder

WORKDIR /app

# Копируем файлы модуля (go.sum добавить, когда появятся внешние зависимости)
COPY go.mod ./
COPY main.go ./

RUN go mod download

# Статическая компиляция:
#   CGO_ENABLED=0  — отключаем CGO, бинарник не линкуется с libc
#   GOOS=linux     — целевая ОС
#   -s             — убираем symbol table
#   -w             — убираем DWARF debug-информацию
ENV CGO_ENABLED=0 GOOS=linux
RUN go build -ldflags="-s -w" -o student-api .

# ─── Stage 2: runner ─────────────────────────────────────────────────────────
FROM scratch

COPY --from=builder /app/student-api /student-api

EXPOSE 8080

ENTRYPOINT ["/student-api"]