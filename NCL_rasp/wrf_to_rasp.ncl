;;; 
;;; Creates RASP NetCDF from WRF_OUT
;;; 
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; Determine Version of NCL we are running
nclv = get_ncl_version()                  ; returns string like 6.0.0 or 5.2.1
nclv_c = stringtochar(nclv)               ; create array of chars
vnum=stringtoint(chartostring(nclv_c(0))) ; turn first char turns into an int

;;; Load NCL scripts
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

; parameter:   GETVAR 
; type:        enviromental variable
; description: determines whether DRJACK's version of wrf_user_getvar is used
; default:     use DRJACK's version
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
Jack = False
if(Jack) then
	print("Loading DrJack wrf_user_mass.ncl")
	loadscript("wrf_user_mass.ncl")
	print("Done")
else
	print("*** WARNING: Using NCL wrf_user_getvar()")
	; Built into NCL
end if

; parameter:   wrfout_file 
; type:        command line argument
; description: full path to WRFOUT file
; default:     
if (.not.isvar("wrfout_file")) then
	print("Error: wrfout_file not specified")
	status_exit(1)
end if

; parameter:   prev_wrfout_file 
; type:        command line argument
; description: full path to previous WRFOUT file for rain calculation
; default:     
if (.not.isvar("prev_wrfout_file")) then
	print("Warning: prev_wrfout_file not specified")
	prev_wrfout_file = ""
end if

; parameter:   output_file
; type:        command line argument
; description: output file full path
if (.not.isvar("output_file")) then
	print("Error: output_file not specified")
	status_exit(1)
end if
if (fileexists(output_file)) then
	print("Error: " + output_file + " already exists")
	status_exit(1)
end if

; parameter:   params
; type:        command line argument
; description: list of parameters to include in output file
if (.not.isvar("params")) then
	print("Error: no parameters not specified")
	status_exit(1)
end if

;; Other Constants
cdbl = 0.003	; Coefficient of Drag for Boundary Layer 
cwbasecriteria = 0.000010	; Cloud Water criterion

; ***********************************************************************************
;;; Load our scripts
load "utils.ncl"

paramList = getParams( params )
print("Plot requested for parameters:")
do p = 0,dimsizes(paramList)-1
	print("    " + paramList(p))
end do

load "calc_funcs.ncl"
load "rasp.ncl"

;****************************************************************

create_rasp_file(wrfout_file, prev_wrfout_file, paramList, output_file)

quit
