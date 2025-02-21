;;; PLOT LAMBERT-CONFORMAL PROJECTION WRF DATA AS MERCATOR PROJECTION IMAGE

;;; PAULS - developed from ...
;;; JACK - altered from http://www.ncl.ucar.edu/Support/talk_archives/2006/1026.html
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; Determine Version of NCL we are running
nclv = get_ncl_version()                  ; returns string like 6.0.0 or 5.2.1
nclv_c = stringtochar(nclv)               ; create array of chars
vnum=stringtoint(chartostring(nclv_c(0))) ; turn first char turns into an int

;;; Load NCL scripts
;;;
;;; Must use loadscript() - not load() - as in a condtional
;;; Load Order is significant
if(vnum .lt. 6) then
	print("NCL VERSION 5")
	print("*** THIS CODE REQUIRES NCL V6")
	print("*** RASP supplies V5")
	print("V6 may be avaliable in your distro")
	print("Try 'yum list ncl' or equivalent")
	exit
else
	loadscript("$NCARG_ROOT/lib/ncarg/nclscripts/wrf/WRFUserARW.ncl")
	loadscript("$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_csm.ncl")
	loadscript("$NCARG_ROOT/lib/ncarg/nclscripts/csm/gsn_code.ncl")
	loadscript("$NCARG_ROOT/lib/ncarg/nclscripts/csm/contributed.ncl")
end if

getvar = getenv("GETVAR")
if(ismissing(getvar)) then
	Jack = True
else
	if(getvar .eq. "DRJACK") then
		Jack = True
	else
		Jack = False
	end if
end if

if(Jack) then
        print("Loading DrJack wrf_user_mass.ncl")
	loadscript("wrf_user_mass.ncl")	; Required if using DrJack's wrf_user_getvar()
        print("Done")
else
	print("*** WARNING: Using NCL wrf_user_getvar()")
	; Built into NCL
end if

; external NCL_JACK_FORTRAN "./ncl_jack_fortran.so"
; test_cuda = False
; NCL_JACK_FORTRAN :: cuda_set_debug(0)
;  NCL_JACK_DEBUG_MEMTIME	2  
;  NCL_JACK_DEBUG_CUDA_MALLOC	4
;  NCL_JACK_DEBUG_COMPARE	8
;  NCL_JACK_DEBUG_DIM		16
;  NCL_JACK_DEBUG_ALL		255
; test_cuda = True
; NCL_JACK_FORTRAN :: cuda_set_debug(255)

;;; *****************************************************************************************
;;; GLOBAL VARIABLES
;;; NB: Global variables MUST appear before any Functions / Procedures in which they are used
;;;     Beware: due to Call By Reference, the func/proc can change value(s)

;;;
;;; Constants for the Whole Run
;;;

CONVERT = getenv("CONVERT") ; Now uses "gm convert" if available, else "convert", as set in runGM script

if (isvar("projection")) then
	Projection = str_lower(getenv(projection))
else
	Projection = "mercator"
end if
if (isvar("region")) then
	Region = region
end if

if (.not.isvar("wrfout_file")) then
	print("Error: wrfout_file not specified")
	status_exit(1)
end if

; get wrfout files
; it can be one when used specific file or
; multiple when wrfout_path contains wild char
cmd = "ls " + wrfout_file
Files = systemfunc(cmd)
delete(cmd)

; check any wrfout files are present
if (dimsizes(Files) .lt. 1) then
	print("Error: no wrfout files found for wrfout_file: " + wrfout_file)
	status_exit(1)
end if

; output file full path
if (.not.isvar("output_path")) then
	print("Error: output_path not specified")
	status_exit(1)
end if
if (.not.fileexists(output_path)) then
	print("Error: " + output_path + " does not exist")
	status_exit(1)
end if

OutDir = output_path + "/"

;;;; Get Output Type
if (isvar("type")) then
	FMT = type
else
	FMT = "png"
end if
print("Output type: " + FMT)


; Specifiy (maximum) Image Width and Height in Pixels
if (.not.isvar("img_size")) then
	wkHeight = 1600.0
	wkWidth  = 1600.0
	print( "Using default image size = " + wkWidth)
else
	wkHeight = tofloat(img_size)
	wkWidth  = tofloat(img_size)
end if

;; Other Constants
time = 0	; Seems time is always 0 for DrJack's code
cdbl = 0.003	; Coefficient of Drag for Boundary Layer 
cwbasecriteria = 0.000010	; Cloud Water criterion

UNITS = "imperial"	; default value - updated by getRegionData() below

opts_ter                 = True
; If you really want terrain contour lines on your plot, uncomment this line
; opts_ter@cnLinesOn       = True
; But if you _don't_ want terrain contour line Labels, also uncomment this line
; opts_ter@cnLineLabelsOn =  False

; ***********************************************************************************
;;; Load our scripts
;;; Order significant :-(

load "utils.ncl"

regionInfo = getRegionData(Region)
UNITS = regionInfo@UNITS
print("UNITS: " + UNITS)

if (.not.isvar("params")) then
	print("Error: no parameters not specified")
	status_exit(1)
end if

ParamList = getParams( params )
print("Plot requested for parameters:")
do p = 0,dimsizes(ParamList)-1
	print("    " + ParamList(p))
end do

load "skewt_func.ncl"
load "calc_funcs.ncl"
load "colourlevels.ncl"
load "wks.ncl"
load "labelbar.ncl"
load "wrf_plot.ncl"
load "plot_funcs.ncl"

;****************************************************************

do fnum = 0, dimsizes(Files)-1
	print("*** Doing " + Files(fnum))
	plot_parameters(Files(fnum) + ".nc", ParamList, regionInfo)
	print("*** Done " + Files(fnum))
end do

; Now do params that run once only for the whole F/C
do p = 0, dimsizes(ParamList)-1
	if(ParamList(p) .eq. "avgstars")
		print("*** Doing avgstars")
		do_avgstars()
	end if
	if(ParamList(p) .eq. "pfd_tot")
		print("*** Doing pfd_tot")
		do_pfd()
	end if
	if(ParamList(p) .eq. "pfd_tot1")
		print("*** Doing pfd_tot1")
		do_pfd1()
	end if
	if(ParamList(p) .eq. "pfd_tot2")
		print("*** Doing pfd_tot2")
		do_pfd2()
	end if
	if(ParamList(p) .eq. "pfd_tot3")
		print("*** Doing pfd_tot3")
		do_pfd3()
	end if
end do

print("NORMAL END of wrf2gm.ncl")

; NCL_JACK_FORTRAN :: ncl_jack_cleanup()

quit
