#ifdef ESP_PLATFORM
  #include <freertos/FreeRTOS.h>
  #include <freertos/queue.h>
  // Simple wrapper to make ESP32 feel like a Pico Queue
  typedef QueueHandle_t queue_t;
  inline void queue_init(queue_t* q, size_t size, size_t count) { *q = xQueueCreate(count, size); }
  inline bool queue_try_add(queue_t* q, void* data) { return xQueueSend(*q, data, 0) == pdPASS; }
  inline bool queue_try_remove(queue_t* q, void* data) { return xQueueReceive(*q, data, 0) == pdPASS; }
#else
  #include <pico/util/queue.h>
#endif