# Stage 1: сборка приложения
FROM golang:1.23-alpine AS builder
WORKDIR /app

# Устанавливаем необходимые пакеты для сборки (gcc, musl-dev)
RUN apk add --no-cache gcc musl-dev

# Копируем файлы модулей и загружаем зависимости
COPY go.mod go.sum ./
RUN go mod download

# Копируем исходный код и собираем приложение
COPY . .
RUN go build -o todo-app .

# Stage 2: минимальный образ для запуска
FROM alpine:3.16
WORKDIR /app
COPY --from=builder /app/todo-app .
# Копируем базу данных, если нужно (например, SQLite)
# COPY --from=builder /app/tasks.db .

EXPOSE 8080
CMD ["./todo-app"]
