
rem dump a library to symgen format

python ..\..\sym_gen.py -d --lib C:\git_bobc\kicad-library\library\cmos_ieee.lib --ref ..\cmos4000\4000_list.csv

if errorlevel 1 goto exit

REM copy /y cmos_ieee_dump.txt cmos_ieee.txt

python ..\..\sym_gen.py --inp cmos_ieee.txt

:exit



