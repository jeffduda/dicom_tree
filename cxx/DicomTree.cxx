#include "DicomTree.hxx"
#include <boost/filesystem.hpp>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/json_parser.hpp>
#include <boost/foreach.hpp>
#include <boost/tokenizer.hpp>
#include <boost/algorithm/string.hpp>
#include <iostream>
#include <string>
#include <algorithm>
#include <vector>
#include <utility>
#include "SimpleITK.h"
#include "itkImageFileReader.h"
#include "itkGDCMImageIO.h"
#include "gdcmReader.h"
#include "gdcmDataElement.h"
#include "gdcmTag.h"
#include "gdcmStringFilter.h"


namespace pt = boost::property_tree;
namespace fs = boost::filesystem;
namespace sitk = itk::simple;

DicomTree::DicomTree() {
    this->m_InputDirectory = "";
    this->m_Output = "";
    this->m_TagFile = "";

    //this->m_TagTree=NULL;
}

void DicomTree::SetInputDirectory(std::string input) {
    this->m_InputDirectory = input;
}

void DicomTree::SetOutput(std::string output) {
    this->m_Output = output;
}

void DicomTree::SetTagFile(std::string tags) {
    this->m_TagFile = tags;
}

void DicomTree::Run() {
    std::cout << "Input: " << this->m_InputDirectory << std::endl;
    std::cout << "TagFile: " << this->m_TagFile<< std::endl;
    std::cout << "Output: " << this->m_Output << std::endl;


    using ImageType = itk::Image<unsigned short, 2>;
    using ReaderType = itk::ImageFileReader<ImageType>;
    using ImageIOType = itk::GDCMImageIO;
    using DictionaryType = itk::MetaDataDictionary;
    using MetaDataStringType = itk::MetaDataObject<std::string>;

    auto itk_reader = ReaderType::New();
    auto dicomIO = ImageIOType::New();
    itk_reader->SetImageIO(dicomIO);

    using GReader = gdcm::Reader;
    const gdcm::Tag pixel_tag(0x7FE0, 0x0010);

    



    // Read in the tags to acquire from the dicom files
    this->GetKeys();
    sitk::ImageFileReader reader;

    std::vector<std::string> file_name;
    std::vector<unsigned long int> file_bytes;
    std::vector<std::string> study_uid;

    std::vector<std::string> series_uid;
    std::vector<std::string> instance_uid;

    std::vector<pt::ptree> instance_nodes;
    
    using StringMap = std::map<std::string, std::string>;
    StringMap series_to_study;
    StringMap instance_to_series;
    std::map<std::string, pt::ptree> instance_to_node;

    // Iterate over the files in the directory
    // Try to read the dicom tags and save them
    for (fs::directory_iterator itr(this->m_InputDirectory); itr!=fs::directory_iterator(); ++itr)
    {
        
        // Read header with sitk
        reader.SetFileName(itr->path().string());
        bool success = true;
        try {
            reader.ReadImageInformation();
        }
        catch ( sitk::GenericException &e ) {
            std::cout << "Error reading image information: " << itr->path().string() << std::endl;
            std::cout << e.what() << std::endl;
            success = false;
        }

        // Read header with gdcm
        GReader gdcm_reader;  // Can't declare this before the loop
        gdcm_reader.SetFileName( itr->path().string().c_str() );
        gdcm::Tag image_type_tag(0x0008, 0x0008);
        bool read = gdcm_reader.ReadUpToTag(pixel_tag);
        if ( !read )
        {
            std::cout << "Could not read: " << itr->path().string() << std::endl;
            return;
        }
        else {
            gdcm::DataSet ds = gdcm_reader.GetFile().GetDataSet();

            if ( ds.FindDataElement(DicomTree::gdcmInstanceUIDTag) &&
                 ds.FindDataElement(DicomTree::gdcmSeriesUIDTag) &&
                 ds.FindDataElement(DicomTree::gdcmStudyUIDTag) ) {
                
                std::string instance_uid_str = this->DataElementValueToString( ds.GetDataElement(DicomTree::gdcmInstanceUIDTag) );
                std::string series_uid_str = this->DataElementValueToString( ds.GetDataElement(DicomTree::gdcmSeriesUIDTag) );
                std::string study_uid_str = this->DataElementValueToString( ds.GetDataElement(DicomTree::gdcmStudyUIDTag) );
                study_uid.push_back(study_uid_str);
                series_uid.push_back(series_uid_str);
                instance_uid.push_back(instance_uid_str);

                // Add the series to study mapping
                if (series_to_study.find(series_uid_str) == series_to_study.end()) {
                    series_to_study[series_uid_str] = study_uid_str;
                }

                // Add the instance to series mapping
                if (instance_to_series.find(instance_uid_str) == instance_to_series.end()) {
                    instance_to_series[instance_uid_str] = series_uid_str;
                }

                pt::ptree node;
                node.put("Filename", itr->path().string());
                std::cout << "Filename: " << itr->path().string() << std::endl;
                std::cout << node.get<std::string>("Filename") << std::endl;
                
                node.put("FileSize", fs::file_size(itr->path()));

                for (const auto& [ikey, ivalue] : m_InstanceMap)
                {
                    //std::cout << '[' << ikey << "] = " << ivalue << "; ";
                    gdcm::Tag itag = this->KeyToTag(ikey);
                    if (ds.FindDataElement(itag)) {
                        pt::ptree value_node = this->DataElementToNode( ikey, ds );
                        node.add_child(ivalue, value_node);
                    }
                }

                //instance_nodes.push_back(node);
                instance_to_node[instance_uid_str] = node;

            }

        }
        
        success=false;


        // Can only parse data with appropriate UID tags
        if (reader.HasMetaDataKey(DicomTree::StudyUIDKey) && 
            reader.HasMetaDataKey(DicomTree::SeriesUIDKey) && 
            reader.HasMetaDataKey(DicomTree::InstanceUIDKey) && success)
        {
            //std::cout << reader.GetMetaData(DicomTree::StudyUIDKey) << std::endl;
            //std::cout << "  " << reader.GetMetaData(DicomTree::SeriesUIDKey) << std::endl;
            //std::cout << "    " << reader.GetMetaData(DicomTree::InstanceUIDKey) << std::endl;
            study_uid.push_back(reader.GetMetaData(DicomTree::StudyUIDKey));
            series_uid.push_back(reader.GetMetaData(DicomTree::SeriesUIDKey));
            instance_uid.push_back(reader.GetMetaData(DicomTree::InstanceUIDKey));

            // Add the series to study mapping
            if (series_to_study.find(reader.GetMetaData(DicomTree::SeriesUIDKey)) == series_to_study.end()) {
                series_to_study[reader.GetMetaData(DicomTree::SeriesUIDKey)] = reader.GetMetaData(DicomTree::StudyUIDKey);
            }

            // Add the instance to series mapping
            if (instance_to_series.find(reader.GetMetaData(DicomTree::InstanceUIDKey)) == instance_to_series.end()) {
                instance_to_series[reader.GetMetaData(DicomTree::InstanceUIDKey)] = reader.GetMetaData(DicomTree::SeriesUIDKey);
            }

            pt::ptree node;
            node.put("Filename", itr->path().string());
            node.put("FileSize", fs::file_size(itr->path()));
            pt::ptree study_node;
            //std::vector<std::string> value_vector;
            //value_vector.push_back(reader.GetMetaData(DicomTree::StudyUIDKey));
            pt::ptree value_list;
            std::string empty_name = "";        
            pt::ptree cell;
            cell.put_value(reader.GetMetaData(DicomTree::StudyUIDKey));
            value_list.push_back(std::make_pair("", cell));
            
            study_node.put("Group", "0020");
            study_node.put("Element", "000E");
            study_node.put("vr", "UI");
            study_node.add_child("Value", value_list);
            node.add_child("StudyInstanceUID", study_node);

            node.put(DicomTree::SeriesUIDKey, reader.GetMetaData(DicomTree::SeriesUIDKey));
            node.put(DicomTree::InstanceUIDKey, reader.GetMetaData(DicomTree::InstanceUIDKey));

            if (reader.HasMetaDataKey("0008|0008"))
                pt::ptree tester = this->KeyToNode( "0008|0008", reader.GetMetaData("0008|0008") );


            instance_nodes.push_back(node);
        }

    }

    std::vector<std::string> unique_study_uid;
    for (StringMap::iterator it=series_to_study.begin(); it!=series_to_study.end(); ++it) {
        std::cout << it->first << " => " << it->second << '\n';
        unique_study_uid.push_back(it->second);
    }
    std::sort(unique_study_uid.begin(), unique_study_uid.end());
    auto last_study = std::unique(unique_study_uid.begin(), unique_study_uid.end());
    unique_study_uid.erase(last_study, unique_study_uid.end());

    std::cout << "Unique Study UIDs: " << unique_study_uid.size() << std::endl;
    std::cout << "Unique Seris UIDs: " << series_to_study.size() << std::endl;


    pt::ptree out_tree;
    out_tree.put("Directory", this->m_InputDirectory);

    pt::ptree study_list;
    std::string empty_name = "";
    for (unsigned int i=0; i<5; i++) {
        pt::ptree cell = instance_to_node[instance_uid[i]];
        study_list.push_back(std::make_pair("",  cell ));
    }
    out_tree.add_child("StudyList", study_list);

    pt::write_json(this->m_Output, out_tree);   

}

std::string DicomTree::DataElementValueToString( gdcm::DataElement de ) {
    std::stringstream strm;
    strm << de.GetValue();
    std::string value = strm.str();
    return(value);
}

gdcm::Tag DicomTree::KeyToTag( std::string key ) 
{
    using Separator = boost::char_separator<char>;
    using Tokenizer = boost::tokenizer<Separator>;
    using TokenIterator = boost::tokenizer<Separator>::iterator;

    Separator key_sep("|");
    Tokenizer key_tokens(key, key_sep);
    TokenIterator key_itr = key_tokens.begin();
    std::string group = *key_itr;
    ++key_itr;
    std::string element = *key_itr;

    std::string gdcm_key = group+","+element;
    gdcm::Tag tag;
    tag.ReadFromCommaSeparatedString(gdcm_key.c_str());
    return(tag);
}

pt::ptree DicomTree::DataElementToNode( std::string key, gdcm::DataSet ds )
{
    using Separator = boost::char_separator<char>;
    using Tokenizer = boost::tokenizer<Separator>;
    using TokenIterator = boost::tokenizer<Separator>::iterator;

    pt::ptree node;
    Separator key_sep("|");
    Separator value_sep("\\");   

    Tokenizer key_tokens(key, key_sep);
    TokenIterator key_itr = key_tokens.begin();
    std::string group = *key_itr;
    ++key_itr;
    std::string element = *key_itr;

    std::string gdcm_key = group+","+element;
    gdcm::Tag tag;
    tag.ReadFromCommaSeparatedString(gdcm_key.c_str());

    gdcm::DataElement de = ds.GetDataElement( tag );
    if (de.IsEmpty()) {
        return node;
    }

    gdcm::VR vr = de.GetVR();
    std::string value = this->DataElementValueToString(de);

    node.put("Group", group);
    node.put("Element", element);
    node.put("vr", std::string(gdcm::VR::GetVRString(vr)));


    // check for a sequence
    if ( vr==gdcm::VR::VRType::SQ ) {


    }
    else {
        pt::ptree value_list;

        if ( vr==gdcm::VR::VRType::US) {
            unsigned short value_entry = this->CastDataElementValue<unsigned short>(de);
            pt::ptree value_entry_node;
            value_entry_node.put_value(value_entry);
            value_list.push_back(std::make_pair("", value_entry_node));
            node.add_child("Value", value_list);
        }
        else if ( vr==gdcm::VR::VRType::SS) {
            signed short value_entry = this->CastDataElementValue<signed short>(de);
            pt::ptree value_entry_node;
            value_entry_node.put_value(value_entry);
            value_list.push_back(std::make_pair("", value_entry_node));
            node.add_child("Value", value_list);
        }        
        else {

            Tokenizer value_tokens(value, value_sep);
            for ( TokenIterator value_itr=value_tokens.begin(); value_itr!=value_tokens.end(); ++value_itr ) {
                std::string value_entry = *value_itr;
                boost::algorithm::trim(value_entry);
                pt::ptree value_entry_node;
                value_entry_node.put_value(value_entry);
                value_list.push_back(std::make_pair("", value_entry_node));
            }
            node.add_child("Value", value_list);
        }
    }
    

    return node;
}

template <typename T>
T DicomTree::CastDataElementValue(gdcm::DataElement de)
{
    const char * ptr = de.GetByteValue()->GetPointer();
    T * value = (T*)ptr;
    return (*value);
}


pt::ptree DicomTree::KeyToNode( std::string key, std::string value ) {

    using Separator = boost::char_separator<char>;
    using Tokenizer = boost::tokenizer<Separator>;
    using TokenIterator = boost::tokenizer<Separator>::iterator;

    pt::ptree node;
    Separator key_sep("|");
    Separator value_sep("\\");   

    Tokenizer key_tokens(key, key_sep);
    TokenIterator key_itr = key_tokens.begin();
    std::string group = *key_itr;
    ++key_itr;
    std::string element = *key_itr;

    node.put("Group", group);
    node.put("Element", element);

    pt::ptree value_list;
    Tokenizer value_tokens(value, value_sep);
    for ( TokenIterator value_itr=value_tokens.begin(); value_itr!=value_tokens.end(); ++value_itr ) {
        std::string value_entry = *value_itr;
        std::cout << "  " << value_entry << " ";
        pt::ptree value_entry_node;
        value_entry_node.put_value(value_entry);
        value_list.push_back(std::make_pair("", value_entry_node));
    }
    std::cout << std::endl;
    node.add_child("Value", value_list);
    return node;

}


std::string DicomTree::indent(int level) {
    std::string s = "";
    for (int i=0; i<level; i++) {
        s += "  ";
    }
    return s;
}

void DicomTree::PrintTags() {
    std::cout << "Printing tags in: " << this->m_TagFile << std::endl;
    pt::ptree pt; 
    pt::read_json(this->m_TagFile, pt);
    this->PrintTree(pt, 2);
}

// Create a map for each category of tags
void DicomTree::KeyMap(pt::ptree pt, std::string map_name)
 {
    MapType map;

    for (pt::ptree::iterator pos = pt.begin(); pos != pt.end();) 
    {
        pt::ptree tag = pos->second;
        std::string tag_group = tag.get_child("Group").data();
        std::string tag_element = tag.get_child("Element").data();
        std::string tag_name = tag.get_child("Name").data();
        std::transform(tag_group.begin(), tag_group.end(), tag_group.begin(), ::tolower);
        std::transform(tag_element.begin(), tag_element.end(), tag_element.begin(), ::tolower);
        std::string tag_key = tag_group + "|" + tag_element;

        //std::cout << tag_key << " -> " << tag_name << std::endl;
        if (map_name == "Study") {
            this->m_StudyMap.insert(std::pair<std::string, std::string>(tag_key, tag_name));
        }
        else if (map_name == "Series") {
            this->m_SeriesMap.insert(std::pair<std::string, std::string>(tag_key, tag_name));
        }
        else if (map_name == "Instance") {
            this->m_InstanceMap.insert(std::pair<std::string, std::string>(tag_key, tag_name));
        }
        ++pos;
    }

 }

void DicomTree::GetKeys() {
    
    pt::ptree pt; 
    pt::read_json(this->m_TagFile, pt);

    this->KeyMap(pt.get_child("Study"), "Study");
    this->KeyMap(pt.get_child("Series"), "Series");
    this->KeyMap(pt.get_child("Instance"), "Instance");    
}

void DicomTree::PrintTree(pt::ptree pt, int level=2)  {

    if (pt.empty()) {
        std::cout << "\""<< pt.data()<< "\"";
    }
    else {
        if (level>0) 
        {
            std::cout << std::endl; 
        }

        for (pt::ptree::iterator pos = pt.begin(); pos != pt.end();) 
        {
            std::cout << this->indent(level+1) << "\"" << pos->first << "\": "; 
            this->PrintTree(pos->second, level+1); 
            ++pos; 

            if (pos != pt.end()) {
                std::cout << ","; 
            }
            std::cout << std::endl;
        } 
        

        //std::cout << "  " << this->indent(level) << " }";     
    }

  return; 
}