# Running symgen

## From command line

```python symgen.py --inp 74xx.txt```
  
where 74xx.txt is a symgen data file.
  
## Convert KiCad lib to symgen data file  

symgen can also convert a kicad .lib file to a symgen .txt file. The conversion is not exact, so the process does not round-trip, but it is useful for creating an initial baseline.

```python symgen.py -d --lib C:\git_bobc\kicad-library\library\74xx.lib```

## Project file

There is a solution file for Microsoft Visual Studio 2015 or similar.

# Examples

See data folder for examples.


# Todos

* update documentation to reflect latest code
