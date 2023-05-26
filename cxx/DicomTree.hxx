#pragma once

#include <boost/property_tree/ptree.hpp>
#include <iostream>
#include <string>
#include <map>
#include "SimpleITK.h"
#include "gdcmDataSet.h"
#include "gdcmTag.h"

namespace sitk = itk::simple;
namespace pt = boost::property_tree;

class DicomTree {
    public:

        using MapType = std::map<std::string, std::string>;

        DicomTree();

        const std::string StudyUIDKey = "0020|000d";
        const std::string SeriesUIDKey = "0020|000e";
        const std::string InstanceUIDKey = "0008|0018";

        const gdcm::Tag gdcmStudyUIDTag = gdcm::Tag(0x0020, 0x000d);
        const gdcm::Tag gdcmSeriesUIDTag = gdcm::Tag(0x0020, 0x000e);
        const gdcm::Tag gdcmInstanceUIDTag = gdcm::Tag(0x0008, 0x0018);


        void SetInputDirectory(std::string input);
        void SetOutput(std::string output);
        void SetTagFile(std::string tags);
        void PrintTree(boost::property_tree::ptree, int level);
        void PrintTags();
        std::string indent(int level);
        void Run();
        void KeyMap(boost::property_tree::ptree, std::string map_name);
        void GetKeys();
        pt::ptree KeyToNode(std::string key, std::string value);
        pt::ptree DataElementToNode(std::string key, gdcm::DataSet ds);
        std::string DataElementValueToString(gdcm::DataElement de);
        gdcm::Tag KeyToTag( std::string key );

        template <typename T>
        T CastDataElementValue(gdcm::DataElement de);

    private:
        std::string m_InputDirectory;
        std::string m_Output;
        std::string m_TagFile;
        MapType m_StudyMap;
        MapType m_SeriesMap;
        MapType m_InstanceMap;


};