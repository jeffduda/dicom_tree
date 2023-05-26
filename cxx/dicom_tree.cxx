/*=========================================================================
 *
 *  Copyright NumFOCUS
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *         https://www.apache.org/licenses/LICENSE-2.0.txt
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License.
 *
 *=========================================================================*/
//  Software Guide : BeginLatex
//
//  The following code is an implementation of a small ITK
//  program. It tests including header files and linking with ITK
//  libraries.
//
//  Software Guide : EndLatex

// Software Guide : BeginCodeSnippet
//#include "itkImage.h"
//#include "itkImageFileReader.h"
//#include "itkGDCMImageIO.h"

#include "SimpleITK.h"
#include "DicomTree.hxx"

#include <iostream>
#include <string>
#include <boost/filesystem.hpp>
#include <boost/program_options.hpp>

namespace po = boost::program_options;
namespace fs = boost::filesystem;
namespace sitk = itk::simple;

int
main(int argc, char** argv)
{

  // Get the input arguments
  std::string input;
  std::string output;
  std::string tags;

  po::options_description desc("Allowed options");
  desc.add_options()
    ("help,h", "produce help message")
    ("input,i", po::value(&input), "set input path")
    ("output,o", po::value(&output), "set output file")
    ("tags,t", po::value(&tags), "tag file");;

  po::variables_map vm;
  po::store(po::command_line_parser(argc, argv).options(desc).run(), vm);
  po::notify(vm);

  if (vm.count("help") || !vm.count("input") || 
      !vm.count("output") || !vm.count("tags")) 
  {
      std::cerr << desc << "\n";
      return 1;
  }


  sitk::ImageFileReader reader;

  std::string studyUIDKey = "0020|000d";
  std::string seriesUIDKey = "0020|000e";
  std::string instanceUIDKey = "0008|0018";

  DicomTree tree;
  tree.SetInputDirectory(input);
  tree.SetOutput(output);
  tree.SetTagFile(tags);
  tree.Run();

  //tree.PrintTags();
  //tree.GetKeys();

  return EXIT_SUCCESS;

  for (fs::directory_iterator itr(input); itr!=fs::directory_iterator(); ++itr)
  {
      std::cout << itr->path().filename() << ' '; // display filename only
      if (is_regular_file(itr->status())) std::cout << " [" << file_size(itr->path()) << ']';
      std::cout << '\n';
      
      reader.SetFileName(itr->path().string());
      reader.ReadImageInformation();
      //std::vector<std::string> keys = reader.GetMetaDataKeys();

      if (reader.HasMetaDataKey(studyUIDKey))
      {
          std::cout << "  " << studyUIDKey << " = " << reader.GetMetaData(studyUIDKey) << std::endl;
      }
      else 
      {
          std::cout << "  " << studyUIDKey << " = " << "None" << std::endl;
      }



      

      //for (unsigned int i = 0; i < keys.size(); i++)
      //{
      //    std::cout << "  " << keys[i] << " = " << reader.GetMetaData(keys[i]) << std::endl;
      //}  
  }
      



  //auto image = ImageType::New();
  //std::cout << "ITK Hello World !" << std::endl;

  return EXIT_SUCCESS;
}
// Software Guide : EndCodeSnippet

//  Software Guide : BeginLatex
//
//  This code instantiates a $3D$ image\footnote{Also known as a
//  \emph{volume}.} whose pixels are represented with type \code{unsigned
//  short}. The image is then constructed and assigned to a
//  \doxygen{SmartPointer}. Although later in the text we will discuss
//  \code{SmartPointer}s in detail, for now think of it as a handle on an
//  instance of an object (see section \ref{sec:SmartPointers} for more
//  information). The \doxygen{Image} class will be described in
//  Section~\ref{sec:ImageSection}.
//
//  Software Guide : EndLatex
