        /* ITK
        itk_reader->SetFileName(itr->path().string());
        dicomIO->SetFileName(itr->path().string());
        dicomIO->ReadImageInformation();

        const DictionaryType & dictionary = dicomIO->GetMetaDataDictionary();
        std::string entryId = "0008|0008";  // ImageType
        auto tagItr = dictionary.Find(entryId);
        if (tagItr != dictionary.End() ) {
            MetaDataStringType::ConstPointer entryvalue = dynamic_cast<const MetaDataStringType *>(tagItr->second.GetPointer());
            
            if (entryvalue)
            {
                std::string tagvalue = entryvalue->GetMetaDataObjectValue();
                std::cout << "ImageType (" << entryId << ") ";
                std::cout << " is: " << tagvalue << std::endl;
            }
        }
        */

       