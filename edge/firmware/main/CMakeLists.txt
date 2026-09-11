idf_component_register(SRCS "main.cpp" "../src/core.cpp" INCLUDE_DIRS "../include" REQUIRES esp_timer)
target_compile_features(${COMPONENT_LIB} PUBLIC cxx_std_17)
