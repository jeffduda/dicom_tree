# This is the root ITK CMakeLists file.
cmake_minimum_required(VERSION 3.16.3 FATAL_ERROR)
foreach(p
    ## Only policies introduced after the cmake_minimum_required
    ## version need to explicitly be set to NEW.
    CMP0070 #3.10.0 Define ``file(GENERATE)`` behavior for relative paths.
    CMP0071 #3.10.0 Let ``AUTOMOC`` and ``AUTOUIC`` process ``GENERATED`` files.
    )
  if(POLICY ${p})
    cmake_policy(SET ${p} NEW)
  endif()
endforeach()


# This project is designed to be built outside the Insight source tree.
project(dicom_tree VERSION 0.1 LANGUAGES CXX)

add_executable(dicom_tree dicom_tree.cxx DicomTree.hxx DicomTree.cxx)

# Find ITK.
find_package(ITK REQUIRED)
include(${ITK_USE_FILE})

find_package(SimpleITK)
find_package( Boost 1.40 COMPONENTS system filesystem program_options REQUIRED )

target_include_directories( dicom_tree PUBLIC ${Boost_INCLUDE_DIR} ${PROJECT_SOURCE_DIR})
target_link_libraries( dicom_tree PUBLIC ${SimpleITK_LIBRARIES} ${Boost_LIBRARIES})
