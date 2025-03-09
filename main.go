package main

import (
    "net/http"
    "github.com/gin-gonic/gin"
    "gorm.io/driver/sqlite"
    "gorm.io/gorm"
)

// Task – структура задачи
type Task struct {
    ID          uint   `json:"id" gorm:"primaryKey"`
    Title       string `json:"title" binding:"required"`
    Description string `json:"description"`
    Completed   bool   `json:"completed"`
}

func main() {
    // Подключение к базе данных (SQLite)
    db, err := gorm.Open(sqlite.Open("tasks.db"), &gorm.Config{})
    if err != nil {
        panic("failed to connect database")
    }
    // Автоматическая миграция схемы
    db.AutoMigrate(&Task{})

    router := gin.Default()

    // Добавление новой задачи: POST /tasks
    router.POST("/tasks", func(c *gin.Context) {
        var task Task
        if err := c.ShouldBindJSON(&task); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        db.Create(&task)
        c.JSON(http.StatusCreated, task)
    })

    // Получение списка задач: GET /tasks
    router.GET("/tasks", func(c *gin.Context) {
        var tasks []Task
        db.Find(&tasks)
        c.JSON(http.StatusOK, tasks)
    })

    // Получение конкретной задачи: GET /tasks/:id
    router.GET("/tasks/:id", func(c *gin.Context) {
        id := c.Param("id")
        var task Task
        if err := db.First(&task, id).Error; err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "Task not found"})
            return
        }
        c.JSON(http.StatusOK, task)
    })

    // Обновление задачи: PUT /tasks/:id
    router.PUT("/tasks/:id", func(c *gin.Context) {
        id := c.Param("id")
        var task Task
        if err := db.First(&task, id).Error; err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "Task not found"})
            return
        }
        var updatedTask Task
        if err := c.ShouldBindJSON(&updatedTask); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        task.Title = updatedTask.Title
        task.Description = updatedTask.Description
        task.Completed = updatedTask.Completed
        db.Save(&task)
        c.JSON(http.StatusOK, task)
    })

    // Удаление задачи: DELETE /tasks/:id
    router.DELETE("/tasks/:id", func(c *gin.Context) {
        id := c.Param("id")
        if err := db.Delete(&Task{}, id).Error; err != nil {
            c.JSON(http.StatusNotFound, gin.H{"error": "Task not found"})
            return
        }
        c.Status(http.StatusNoContent)
    })

    // Запуск сервера на порту 8080
    router.Run(":8080")
}
