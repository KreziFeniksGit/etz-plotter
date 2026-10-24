#include "Settings.h"
#include "nvs_flash.h"
#include "nvs.h"

static const char *NS = "etz";            // our namespace in the NVS partition

namespace Settings {

bool begin() {
  esp_err_t e = nvs_flash_init();
  if (e == ESP_ERR_NVS_NO_FREE_PAGES || e == ESP_ERR_NVS_NEW_VERSION_FOUND) {   // full or old format: start clean
    nvs_flash_erase();
    e = nvs_flash_init();
  }
  return e == ESP_OK;
}

bool save(const char *name, const void *data, size_t len) {
  nvs_handle_t h;
  if (nvs_open(NS, NVS_READWRITE, &h) != ESP_OK) return false;
  bool ok = nvs_set_blob(h, name, data, len) == ESP_OK && nvs_commit(h) == ESP_OK;
  nvs_close(h);
  return ok;
}

bool load(const char *name, void *data, size_t len) {
  nvs_handle_t h;
  if (nvs_open(NS, NVS_READONLY, &h) != ESP_OK) return false;
  size_t n = 0;
  bool ok = nvs_get_blob(h, name, nullptr, &n) == ESP_OK && n == len && nvs_get_blob(h, name, data, &n) == ESP_OK;
  nvs_close(h);
  return ok;
}

bool remove(const char *name) {
  nvs_handle_t h;
  if (nvs_open(NS, NVS_READWRITE, &h) != ESP_OK) return false;
  bool ok = nvs_erase_key(h, name) == ESP_OK && nvs_commit(h) == ESP_OK;
  nvs_close(h);
  return ok;
}

void list(void (*fn)(const char *name)) {
  nvs_iterator_t it = nullptr;
  esp_err_t e = nvs_entry_find(NVS_DEFAULT_PART_NAME, NS, NVS_TYPE_BLOB, &it);
  while (e == ESP_OK) {
    nvs_entry_info_t info;
    nvs_entry_info(it, &info);
    fn(info.key);
    e = nvs_entry_next(&it);
  }
  nvs_release_iterator(it);
}

}
