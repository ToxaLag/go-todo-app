package main

import (
    "bytes"
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "testing"

    "github.com/gin-gonic/gin"
    "gorm.io/driver/sqlite"
    "gorm.io/gorm"
)

// setupRouter инициализирует роутер для тестов с in‑memory базой
func setupRouter() *gin.Engine {
    gin.SetMode(gin.TestMode)
    db, _ := gorm.Open(sqlite.Open("file::memory:?cache=shared"), &gorm.Config{})
    db.AutoMigrate(&Task{})

    router := gin.Default()

    router.POST("/tasks", func(c *gin.Context) {
        var task Task
        if err := c.ShouldBindJSON(&task); err != nil {
            c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
            return
        }
        db.Create(&task)
        c.JSON(http.StatusCreated, task)
    })

    return router
}

func TestCreateTask(t *testing.T) {
    router := setupRouter()

    newTask := Task{
        Title:       "Test task",
        Description: "This is a test",
        Completed:   false,
    }
    jsonValue, _ := json.Marshal(newTask)
    req, _ := http.NewRequest("POST", "/tasks", bytes.NewBuffer(jsonValue))
    req.Header.Set("Content-Type", "application/json")
    w := httptest.NewRecorder()
    router.ServeHTTP(w, req)

    if w.Code != http.StatusCreated {
        t.Errorf("Expected status %d, got %d", http.StatusCreated, w.Code)
    }
}
