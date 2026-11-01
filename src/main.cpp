#include <cstdio>
#include "esp_camera.h"
#include "esp_event.h"
#include "esp_heap_caps.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_psram.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

// EJEMPLO: cableado de cámara tipo ESP32-S3-EYE. NO es un pinout universal.
// Sustituye TODOS los GPIO según el esquema de tu módulo/placa antes de conectar.
// D0-D7 equivalen a Y2-Y9 del sensor. Evita GPIO de Flash/PSRAM (26-37
// en módulos N16R8 según módulo), USB y pines de arranque según tu placa.
#define CAM_D0 11
#define CAM_D1 9
#define CAM_D2 8
#define CAM_D3 10
#define CAM_D4 12
#define CAM_D5 18
#define CAM_D6 17
#define CAM_D7 16
#define CAM_VSYNC 6
#define CAM_HREF 7
#define CAM_PCLK 13
#define CAM_XCLK 15
#define CAM_SIOC 5
#define CAM_SIOD 4
#define CAM_PWDN -1
#define CAM_RESET -1

static const char *TAG = "teleop";
static constexpr char BOUNDARY[] = "teleop_frame_boundary";

static esp_err_t stream_handler(httpd_req_t *req) {
    esp_err_t err = httpd_resp_set_type(req,
        "multipart/x-mixed-replace;boundary=teleop_frame_boundary");
    if (err != ESP_OK) return err;
    httpd_resp_set_hdr(req, "Cache-Control", "no-store, no-cache, must-revalidate");
    while (true) {
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) return ESP_FAIL;
        if (fb->format != PIXFORMAT_JPEG) {
            esp_camera_fb_return(fb);
            return ESP_FAIL;
        }
        char header[160];
        const int len = snprintf(header, sizeof(header),
            "\r\n--%s\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
            BOUNDARY, static_cast<unsigned>(fb->len));
        if (len < 0 || len >= static_cast<int>(sizeof(header))) {
            esp_camera_fb_return(fb);
            return ESP_FAIL;
        }
        err = httpd_resp_send_chunk(req, header, len);
        if (err == ESP_OK)
            err = httpd_resp_send_chunk(req, reinterpret_cast<const char *>(fb->buf), fb->len);
        // Liberar siempre el buffer, incluso al desconectarse la estación.
        esp_camera_fb_return(fb);
        if (err != ESP_OK) return err;
    }
}

static void init_wifi() {
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_t *ap = esp_netif_create_default_wifi_ap();
    ESP_ERROR_CHECK(ap ? ESP_OK : ESP_ERR_NO_MEM);
    ESP_ERROR_CHECK(esp_netif_dhcps_stop(ap));
    esp_netif_ip_info_t ip{};
    IP4_ADDR(&ip.ip, 192, 168, 4, 1);
    IP4_ADDR(&ip.gw, 192, 168, 4, 1);
    IP4_ADDR(&ip.netmask, 255, 255, 255, 0);
    ESP_ERROR_CHECK(esp_netif_set_ip_info(ap, &ip));
    ESP_ERROR_CHECK(esp_netif_dhcps_start(ap));
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    wifi_config_t config{};
    snprintf(reinterpret_cast<char *>(config.ap.ssid), sizeof(config.ap.ssid), "ESP32S3_Teleop_Net");
    snprintf(reinterpret_cast<char *>(config.ap.password), sizeof(config.ap.password), "123456789");
    config.ap.channel = 6;
    config.ap.max_connection = 1;
    config.ap.authmode = WIFI_AUTH_WPA2_PSK;
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &config));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
}

extern "C" void app_main() {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
    if (!esp_psram_is_initialized() || esp_psram_get_size() < 8 * 1024 * 1024) {
        ESP_LOGE(TAG, "Se requieren 8MB PSRAM OPI inicializados. Revisar módulo y sdkconfig.");
        return;
    }
    ESP_LOGI(TAG, "PSRAM: %u bytes; libre: %u", unsigned(esp_psram_get_size()),
             unsigned(heap_caps_get_free_size(MALLOC_CAP_SPIRAM)));
    camera_config_t cam{};
    cam.pin_d0 = CAM_D0; cam.pin_d1 = CAM_D1;
    cam.pin_d2 = CAM_D2; cam.pin_d3 = CAM_D3;
    cam.pin_d4 = CAM_D4; cam.pin_d5 = CAM_D5;
    cam.pin_d6 = CAM_D6; cam.pin_d7 = CAM_D7;
    cam.pin_vsync = CAM_VSYNC; cam.pin_href = CAM_HREF;
    cam.pin_pclk = CAM_PCLK; cam.pin_xclk = CAM_XCLK;
    cam.pin_sccb_sda = CAM_SIOD; cam.pin_sccb_scl = CAM_SIOC;
    cam.pin_pwdn = CAM_PWDN; cam.pin_reset = CAM_RESET;
    cam.xclk_freq_hz = 20000000;
    cam.ledc_timer = LEDC_TIMER_0; cam.ledc_channel = LEDC_CHANNEL_0;
    cam.pixel_format = PIXFORMAT_JPEG;
    cam.frame_size = FRAMESIZE_VGA;
    cam.jpeg_quality = 12;
    cam.fb_count = 2;
    cam.fb_location = CAMERA_FB_IN_PSRAM;
    cam.grab_mode = CAMERA_GRAB_LATEST;
    err = esp_camera_init(&cam);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Cámara no inicializada: %s. Revisar GPIO, alimentación y sensor.", esp_err_to_name(err));
        return;
    }
    init_wifi();
    httpd_config_t server_config = HTTPD_DEFAULT_CONFIG();
    server_config.server_port = 81;
    server_config.max_open_sockets = 2;
    server_config.lru_purge_enable = true;
    server_config.send_wait_timeout = 2;
    httpd_handle_t server = nullptr;
    ESP_ERROR_CHECK(httpd_start(&server, &server_config));
    httpd_uri_t uri{};
    uri.uri = "/stream"; uri.method = HTTP_GET; uri.handler = stream_handler;
    ESP_ERROR_CHECK(httpd_register_uri_handler(server, &uri));
    ESP_LOGI(TAG, "MJPEG disponible en http://192.168.4.1:81/stream (un cliente)");
}
