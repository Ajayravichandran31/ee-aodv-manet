build_lib_example(
  NAME eeaodv
  SOURCE_FILES eeaodv.cc
  LIBRARIES_TO_LINK
    ${libwifi}
    ${libinternet}
    ${libeeaodv}
    ${libinternet-apps}
)
