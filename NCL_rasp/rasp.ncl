load "$NCARG_ROOT/lib/ncarg/nclscripts/wrf/WRF_contributed.ncl"

function createRASPVar_float_XY(inVar[*][*]:float, description:string, units:string)
local var, inVarDims
begin
	inVarDims = dimsizes(inVar)
	var = new((/1, inVarDims(0), inVarDims(1)/), float, getFillValue(inVar))
	var@FieldType = 104
	var@MemoryOrder = "XY "
	var@description = description
	var@units = units
	var@stagger = ""
	var@coordinates = "XLONG XLAT XTIME"
	
	var = conform_dims(dimsizes(var), inVar, (/1, 2/))
	var!0 = "Time"
	var!1 = "south_north"
	var!2 = "west_east"
	
	if(isatt(var,"_FillValue")) then
		delete(var@_FillValue)
	end if
	return var
end

function createRASPVar_float_XYZ(inVar[*][*][*]:float, description:string, units:string)
local var, inVarDims
begin
	inVarDims = dimsizes(inVar)
	var = new((/1, inVarDims(0), inVarDims(1), inVarDims(2)/), float, getFillValue(inVar))
	var@FieldType = 104
	var@MemoryOrder = "XYZ"
	var@description = description
	var@units = units
	var@stagger = ""
	var@coordinates = "XLONG XLAT XTIME"
	
	var = conform_dims(dimsizes(var), inVar, (/1, 2, 3/))
	var!0 = "Time"
	var!1 = "bottom_top"
	var!2 = "south_north"
	var!3 = "west_east"
	
	if(isatt(var,"_FillValue")) then
		delete(var@_FillValue)
	end if
	return var
end

r2dConst = 45.0/atan(1.0)
function calcWindDirection(u:float, v:float)
begin
	if (isdefined("get_r2d")) then
		return 180.0 + get_r2d(u) * atan2(u, v)
	else
		return 180.0 + r2dConst * atan2(u, v)
	end if
end

function calcWindSpeed(u:float, v:float)
begin
	return sqrt(u*u + v*v)
end

function calcRain1Acc(f, prev_wrfout_file, nx, ny)
begin
	acctime = 1

	rainc  = f->RAINC
	rainnc = f->RAINNC
	rainc  = rainc > 0.0
	rainnc = rainnc > 0.0

	rainTot = new ( (/ny, nx/), float)

	;; If the previous file exists -> load it, subtract earlier rain, plot it.
	if (isfilepresent(prev_wrfout_file)) then
		prevfile = addfile( prev_wrfout_file+".nc", "r" )

		prevrainc  = prevfile->RAINC
		prevrainnc = prevfile->RAINNC

		; Use NCL operator > to make sure all values >=0.0
		prevrainc  = prevrainc > 0.0
		prevrainnc = prevrainnc > 0.0

		rainTot = rainc + rainnc - prevrainc - prevrainnc
	else
		rainTot = rainc + rainnc
	end if
	return(rainTot)
end

procedure getBLWind()
begin
end

procedure create_rasp_file(wrfout_file, prev_wrfout_file, params, output_file)
begin

	; open input wrfout file
	f = addfile(wrfout_file + ".nc", "r")

	; Inline code, so variables are local => discarded on exit from procedure
	load "getvars.ncl"	
	
	; open output file
	fout = addfile(output_file, "c")  
	
    ; explicitly declare file definition mode. Improve efficiency.
    setfileoption(fout, "DefineMode", True)	
	
	; create global attributes of the file
	; global attributes are copied from WRFOUT file 
	; without modification except the TITLE
	foutAtts = True
	copy_VarAtts(f, foutAtts)
	foutAtts@TITLE = "RASP OUTPUT (" + foutAtts@TITLE + ")"
	fileattdef(fout, foutAtts)

	; copy coordinate variables and their dimensionality from WRFOUT
    dimNames = getvardims(f)
	dimSizes = getfiledimsizes(f)
	dimUnlim = new(dimsizes(dimNames), logical)
	do i = 0, dimsizes(dimNames) - 1
		if (dimNames(i) .eq. "Time") then
			dimUnlim(i) = True
		else
			dimUnlim(i) = False
		end if
	end do
	filedimdef(fout, dimNames, dimSizes, dimUnlim)

	; Times
	filevardef(fout, "times" , typeof(f->Times), getvardims(f->Times)) 
	fout->times = f->Times
	
	; initialize var to anything
	do i = 0, dimsizes(params) - 1
	
		if (isfilevar(fout, params(i))) then
			continue
		end if
		
		if (isvar("var")) then
			delete(var)
		end if
		
		if (params(i) .eq. "xlat" ) then
			filevardef(fout, "xlat" , typeof(f->XLAT), getvardims(f->XLAT)) 
			fout->xlat = f->XLAT
			continue
		end if
	
		if (params(i) .eq. "xlong" ) then
			filevardef(fout, "xlong" , typeof(f->XLONG), getvardims(f->XLONG)) 
			fout->xlong = f->XLONG
			continue
		end if
	
		if (params(i) .eq. "terhgt" ) then
			filevardef(fout, "terhgt" , typeof(f->HGT), getvardims(f->HGT)) 
			fout->terhgt = f->HGT
			continue
		end if
	
		if (params(i) .eq. "geophgt" ) then
			geopotentialHeight = wrf_user_getvar(f,"z", 0)
			var = createRASPVar_float_XYZ(geopotentialHeight, "Geopotential height", "m")
			filevardef(fout, "geophgt", typeof(var), getvardims(var))
			fout->geophgt = var
			continue
		end if
	
		if (params(i) .eq. "pressure" ) then
			filevardef(fout, "pressure" , typeof(f->P), getvardims(f->P)) 
			fullPressure = f->P + f->PB
			copy_VarAtts(f->P, fullPressure)
			fullPressure@description = "Full pressure"
			fout->pressure = fullPressure
			continue
		end if
	
		if (params(i) .eq. "rain1" ) then
			rain1Var = calcRain1Acc(f, prev_wrfout_file, nx, ny)
			var = createRASPVar_float_XY(rain1Var, "1 hour rain accumulation", "mm")
			filevardef(fout, "rain1", typeof(var), getvardims(var)) 	
			fout->rain1 = var
			continue
		end if
		
		if (params(i) .eq. "zblcl") then
			if( .not. isvar("zblclVar")) then
				zblclVar = zblcl(qvapor, z, ter, pblh, pmb, tc, nx, ny, nz)
			end if
			var = createRASPVar_float_XY(zblclVar, "Overcast Development Cloudbase", "m")
			filevardef(fout, "zblcl", typeof(var), getvardims(var))
			fout->zblcl = var
			continue
		end if

		if (params(i) .eq. "zblcldif") then
			if( .not. isvar("zblclVar")) then
				zblclVar = zblcl(qvapor, z, ter, pblh, pmb, tc, nx, ny, nz)
			end if
			if( .not. isvar("zblcldifVar")) then
				zblcldifVar = zblcldif(ter, pblh, zblclVar)
			end if
			var = createRASPVar_float_XY(zblcldifVar, "Overcast Development Potential", "m")
			filevardef(fout, "zblcldif", typeof(var), getvardims(var))
			fout->zblcldif = var
			continue
		end if
		
		if (params(i) .eq. "zblclmask") then
			if( .not. isvar("zblclVar")) then
				zblclVar = zblcl(qvapor, z, ter, pblh, pmb, tc, nx, ny, nz)
			end if
			if( .not. isvar("zblcldifVar")) then
				zblcldifVar = zblcldif(ter, pblh, zblclVar)
			end if
			zblclVar@_FillValue = 0.0
			zblclmaskVar = mask(zblclVar, (zblcldifVar .ge. 0), True)
			var = createRASPVar_float_XY(zblclmaskVar, "OD Cloudbase where OD Potential > 0", "m")
			filevardef(fout, "zblclmask", typeof(var), getvardims(var))
			fout->zblclmask = var
			continue
		end if

		if (params(i) .eq. "zsfclcl") then
			if (.not. isvar("zsfclclVar")) then
				zsfclclVar = zsfclcl(pmb, tc, td, z, ter, pblh, nx, ny, nz)
			end if
			var = createRASPVar_float_XY(zsfclclVar, "Cu Cloudbase (Sfc. LCL)", "m")
			filevardef(fout, "zsfclcl", typeof(var), getvardims(var))
			fout->zsfclcl = var
			continue
		end if

		if (params(i) .eq. "zsfclcldif") then
			if (.not. isvar("zsfclclVar")) then
				zsfclclVar = zsfclcl(pmb, tc, td, z, ter, pblh, nx, ny, nz)
			end if
			if (.not. isvar("zsfclcldifVar")) then
				zsfclcldifVar = zsfclcldif(ter, pblh, zsfclclVar)
			end if
			var = createRASPVar_float_XY(zsfclcldifVar, "Cu Potential", "m")
			filevardef(fout, "zsfclcldif", typeof(var), getvardims(var))
			fout->zsfclcldif = var
			continue
		end if
		
		if (params(i) .eq. "zsfclclmask") then
			if (.not. isvar("zsfclclVar")) then
				zsfclclVar = zsfclcl(pmb, tc, td, z, ter, pblh, nx, ny, nz)
			end if
			if (.not. isvar("zsfclcldifVar")) then
				zsfclcldifVar = zsfclcldif(ter, pblh, zsfclclVar)
			end if
			zsfclclVar@_FillValue = 0.0
			zsfclclmaskVar = mask(zsfclclVar, (zsfclcldifVar .ge. 0), True)
			var = createRASPVar_float_XY(zsfclclmaskVar, "OD Cloudbase where OD Potential > 0", "m")
			filevardef(fout, "zsfclclmask", typeof(var), getvardims(var))
			fout->zsfclclmask = var
			continue
		end if
		
		if (params(i) .eq. "cloudsuck") then
			cloudsuckVar = cloudsuck(rqcblten, mu, mub, z, ter, pblh, nx, ny, nz)
			var = createRASPVar_float_XY(cloudsuckVar, "Cloud Condensation Equiv Heat", "")
			filevardef(fout, "cloudsuck", typeof(var), getvardims(var))
			fout->cloudsuck = var
			continue
		end if
		
		if (params(i) .eq. "aboveblicw") then
			aboveblicwVar = aboveblicw(qcloud, ppert, pb, z, ter, pblh, nx, ny, nz)
			var = createRASPVar_float_XY(aboveblicwVar, "Integrated Cloud Water Above BL", "g")
			filevardef(fout, "aboveblicw", typeof(var), getvardims(var))
			fout->aboveblicw = var
			continue
		end if
		
		if (params(i) .eq. "sfcshf") then
			var = createRASPVar_float_XY(hfx, "Sfc. Heating", "W/m2")
			filevardef(fout, "sfcshf", typeof(var), getvardims(var))
			fout->sfcshf = var
			continue
		end if
		
		if (params(i) .eq. "hbl") then
			hblVar = pblh + ter
			var = createRASPVar_float_XY(hblVar, "Height of BL Top", "m")
			filevardef(fout, "hbl", typeof(var), getvardims(var))
			fout->hbl = var
			continue
		end if
		
		if (params(i) .eq. "blcloudpct") then
			blcloudpctVar = blcloudpct(qvapor, qcloud, tc, pmb, z, ter, pblh, cwbasecriteria, nx, ny, nz)
			var = createRASPVar_float_XY(blcloudpctVar, "BL Cloud Cover", "%")
			filevardef(fout, "blcloudpct", typeof(var), getvardims(var))
			fout->blcloudpct = var
			continue
		end if
		
		if (params(i) .eq. "blicw") then
			blicwVar = blicw(qcloud, ppert, pb, psfc, z, pblh, ter, nx, ny, nz)
			var = createRASPVar_float_XY(blicwVar, "BL Integrated Cloud Water", "g")
			filevardef(fout, "blicw", typeof(var), getvardims(var))
			fout->blicw = var
			continue
		end if
		
		if (params(i) .eq. "bltopvariab") then
			bltopvariabVar = bltopvariab(thetac, z, pblh, ter, nx, ny, nz)
			var = createRASPVar_float_XY(bltopvariabVar, "BL Top Uncertainty/Variability (for +1degC)", "m")
			filevardef(fout, "bltopvariab", typeof(var), getvardims(var))
			fout->bltopvariab = var
			continue
		end if
		
		if (params(i) .eq. "blwindshear") then
			blwindshearVar = blwindshear(ua, va, z, ter, pblh, nx, ny, nz)
			var = createRASPVar_float_XY(blwindshearVar, "BL Vertical Wind Shear", "m/s")
			filevardef(fout, "blwindshear", typeof(var), getvardims(var))
			fout->blwindshear = var
			continue
		end if
		
		if (params(i) .eq. "wstar") then
			if( .not. isvar("wstarVar")) then
				wstarVar = wstar(nx, ny, nz, vhf, pblh, hfx, tc )
			end if
			var = createRASPVar_float_XY(wstarVar, "Thermal Updraft Velocity (W*)", "m/s")
			filevardef(fout, "wstar", typeof(var), getvardims(var))
			fout->wstar = var
			continue
		end if
		
		if (params(i) .eq. "experimental2") then
			experimental2Var = experimental2(cldfra, z, ter, pblh, nx, ny, nz)
			var = createRASPVar_float_XY(experimental2Var, "BL Cloud Fraction", "%")
			filevardef(fout, "experimental2", typeof(var), getvardims(var))
			fout->experimental2 = var
			continue
		end if
		
		if (params(i) .eq. "experimental1") then
			if( .not. isvar("wstarVar")) then
				wstarVar = wstar(nx, ny, nz, vhf, pblh, hfx, tc )
			end if
			experimental1Var = experimental1(wstarVar, ter, pblh, nx, ny)
			var = createRASPVar_float_XY(experimental1Var, "H_lift for 175fpm sinkrate", "m")
			filevardef(fout, "experimental1", typeof(var), getvardims(var))
			fout->experimental1 = var
			continue
		end if
		
		if (params(i) .eq. "hwcrit") then
			if( .not. isvar("wstarVar")) then
				wstarVar = wstar(nx, ny, nz, vhf, pblh, hfx, tc)
			end if
			hwcritVar = hwcrit(wstarVar, ter, pblh, nx, ny)
			var = createRASPVar_float_XY(hwcritVar, "Height of Critical Updraft Strength (Hcrit)", "m")
			filevardef(fout, "hwcrit", typeof(var), getvardims(var))
			fout->hwcrit = var
			continue
		end if
		
		if (params(i) .eq. "hglider") then
			if (.not. isvar("hgliderVar") ) then
				if (.not. isvar("hwcritVar")) then
					if (.not. isvar("wstarVar")) then
						wstarVar = wstar(nx, ny, nz, vhf, pblh, hfx, tc)
					end if
					hwcritVar = hwcrit(wstarVar, ter, pblh, nx, ny)
				end if
				if( .not. isvar("zsfclclVar")) then
					zsfclclVar = zsfclcl(pmb, tc, td, z, ter, pblh, nx, ny, nz)
				end if
				if( .not. isvar("zblclVar")) then
					zblclVar = zblcl( qvapor, z, ter, pblh, pmb, tc, nx, ny, nz)
				end if
				hgliderVar = hglider(hwcritVar, zsfclclVar, zblclVar, nx, ny)
			end if
			var = createRASPVar_float_XY(hgliderVar, "Thermalling Height", "m")
			filevardef(fout, "hglider", typeof(var), getvardims(var))
			fout->hglider = var
			continue
		end if

		if (params(i) .eq. "umet") then
			if (isfilevar(fout, "umet")) then
				continue
			end if
			
			var = createRASPVar_float_XYZ(uEW, "U component of wind rotated to earth coordinates", "m/s")
			filevardef(fout, "umet", typeof(var), getvardims(var))
			fout->umet = var
			continue		
		end if
		
		if (params(i) .eq. "vmet") then
			if (isfilevar(fout, "vmet")) then
				continue
			end if
			
			var = createRASPVar_float_XYZ(vNS, "V component of wind rotated to earth coordinates", "m/s")
			filevardef(fout, "vmet", typeof(var), getvardims(var))
			fout->vmet = var
			continue		
		end if
		
		if (params(i) .eq. "metwindspd") then
			if (isfilevar(fout, "metwindspd")) then
				continue
			end if
			
			uvmetSpd = calcWindSpeed(uEW, vNS)
			var = createRASPVar_float_XYZ(uvmetSpd, "Speed of wind rotated to earth coordinates", "m/s")
			filevardef(fout, "metwindspd", typeof(var), getvardims(var))
			fout->metwindspd = var
			continue		
		end if
		
		if (params(i) .eq. "metwinddir") then
			if (isfilevar(fout, "metwinddir")) then
				continue
			end if
			
			uvmetDir = calcWindDirection(uEW, vNS)
			var = createRASPVar_float_XYZ(uvmetDir, "Direction of wind rotated to earth coordinates", "deg")
			filevardef(fout, "metwinddir", typeof(var), getvardims(var))
			fout->metwinddir = var
			continue		
		end if
		
		if (params(i) .eq. "metwind10spd") then
			if (isfilevar(fout, "metwind10spd")) then
				continue
			end if
			
			if (.not. isvar("uvmet10WSpdWDir")) then
				uvmet10 = wrf_user_getvar(f, "uvmet10", time)
			end if
			
			metWind10Spd = calcWindSpeed(uvmet10(0,:,:), uvmet10(0,:,:))
			var = createRASPVar_float_XY(metWind10Spd, "Speed of wind at 10m rotated to earth coordinates", "m/s")
			filevardef(fout, "metwind10spd", typeof(var), getvardims(var))
			fout->metwind10spd = var
			continue		
		end if

		if (params(i) .eq. "metwind10dir") then
			if (isfilevar(fout, "metwind10dir")) then
				continue
			end if
			
			if ( .not. isvar("uvmet10WSpdWDir")) then
				uvmet10 = wrf_user_getvar(f, "uvmet10", time)
			end if
			
			metWind10Dir = calcWindDirection(uvmet10(0,:,:), uvmet10(0,:,:))
			var = createRASPVar_float_XY(metWind10Dir, "Direction of wind at 10m rotated to earth coordinates", "deg")
			filevardef(fout, "metwind10dir", typeof(var), getvardims(var))
			fout->metwind10dir = var
			continue		
		end if

		if (params(i) .eq. "bltopwindspd") then
			if (isfilevar(fout, "bltopwindspd")) then
				continue
			end if
			
			if( .not. isvar("bltopwindU")) then
				bltopwindU = new ((/ny, nx/), float)
				bltopwindV = new ((/ny, nx/), float)
				bltopwindSpeed = new ((/ny, nx/), float)
				bltopwind(uEW, vNS, z, ter, pblh, nx, ny, nz, bltopwindU, bltopwindV, bltopwindSpeed)
			end if
		
			var = createRASPVar_float_XY(bltopwindSpeed, "BL Top Wind Speed", "m/s")
			filevardef(fout, "bltopwindspd", typeof(var), getvardims(var))
			fout->bltopwindspd = var
			continue
		end if
		
		if (params(i) .eq. "bltopwinddir") then
			if (isfilevar(fout, "bltopwinddir")) then
				continue
			end if
			if( .not. isvar("bltopwindU")) then
				bltopwindU = new ((/ny, nx/), float)
				bltopwindV = new ((/ny, nx/), float)
				bltopwindSpeed = new ((/ny, nx/), float)
				bltopwind(uEW, vNS, z, ter, pblh, nx, ny, nz, bltopwindU, bltopwindV, bltopwindSpeed)
			end if
			bltopwindDir = calcWindDirection(bltopwindU, bltopwindV)
		
			var = createRASPVar_float_XY(bltopwindDir, "BL Top Wind Direction", "deg")
			filevardef(fout, "bltopwinddir", typeof(var), getvardims(var))
			fout->bltopwinddir = var
			continue
		end if
		
		if (params(i) .eq. "blwindspd") then
			if (isfilevar(fout, "blwindspd")) then
				continue
			end if
			
			if( .not. isvar("blwindU")) then
				blwindU = new ((/ny, nx/), float)
				blwindV = new ((/ny, nx/), float)
				blwindSpeed = new ((/ny, nx/), float)
				blwind(z, ter, pblh, nx, ny, nz, uEW, vNS, blwindSpeed, blwindU, blwindV)
			end if

			var = createRASPVar_float_XY(blwindSpeed, "BL Average Wind Speed", "m/s")
			filevardef(fout, "blwindspd", typeof(var), getvardims(var))
			fout->blwindspd = var
			continue
		end if		
		
		if (params(i) .eq. "blwinddir") then
			if (isfilevar(fout, "blwinddir")) then
				continue
			end if

			if( .not. isvar("blwindU")) then
				blwindU = new ((/ny, nx/), float)
				blwindV = new ((/ny, nx/), float)
				blwindSpeed = new ((/ny, nx/), float)
				blwind(z, ter, pblh, nx, ny, nz, uEW, vNS, blwindSpeed, blwindU, blwindV)
			end if
			blwindDir = calcWindDirection(blwindU, blwindV)
			
			var = createRASPVar_float_XY(blwindDir, "BL Average Wind Direction", "deg")
			filevardef(fout, "blwinddir", typeof(var), getvardims(var))
			fout->blwinddir = var
			continue
		end if		
		
		if (params(i) .eq. "bsratio") then
			if (isfilevar(fout, "bsratio")) then
				continue
			end if
			
			if( .not. isvar("blwindU")) then
				blwindU = new ((/ny, nx/), float)
				blwindV = new ((/ny, nx/), float)
				blwindSpeed = new ((/ny, nx/), float)
				blwind(z, ter, pblh, nx, ny, nz, uEW, vNS, blwindSpeed, blwindU, blwindV)
			end if

			if (.not. isvar("wstarVar")) then
				wstarVar = wstar(nx, ny, nz, vhf, pblh, hfx, tc)
			end if
			
			bsratioVar = bsratio(blwindSpeed, wstarVar)
			var = createRASPVar_float_XY(bsratioVar, "Buoyancy/Shear Ratio", "")
			filevardef(fout, "bsratio", typeof(var), getvardims(var))
			fout->bsratio = var
			continue
		end if	
		
		if (params(i) .eq. "wblmaxmin") then
			wblmaxminVar = wblmaxmin(wa, z, ter, pblh, nx, ny, nz)
			var = createRASPVar_float_XY(wblmaxminVar, "BL Max. Up/Down Motion", "cm/s")
			filevardef(fout, "wblmaxmin", typeof(var), getvardims(var))
			fout->wblmaxmin = var
			continue
		end if
		
		if (params(i) .eq. "zwblmaxmin") then
			zwblmaxminVar = zwblmaxmin(wa, z, ter, pblh, nx, ny, nz)
			var = createRASPVar_float_XY(zwblmaxminVar, "MSL Height of maxmin Wbl", "m")
			filevardef(fout, "zwblmaxmin", typeof(var), getvardims(var))
			fout->zwblmaxmin = var
			continue
		end if		
		
		if (params(i) .eq. "mslpress") then
			var = createRASPVar_float_XY(slvl, "Mean Sea Level Pressure", "hPa")
			filevardef(fout, "mslpress", typeof(var), getvardims(var))
			fout->mslpress = var
			continue
		end if		
				
		if (params(i) .eq. "cape") then
			capeVar = cape(pmb, tc, td, nx, ny, nz)
			var = createRASPVar_float_XY(capeVar, "Convective Available Potential Energy (CAPE)", "J/kg")
			filevardef(fout, "cape", typeof(var), getvardims(var))
			fout->cape = var
			continue
		end if		

		if (params(i) .eq. "sfctemp") then
			sfctempVar = tc2 - 273.16
			var = createRASPVar_float_XY(sfctempVar, "Surface Temperature (2m AGL)", "C")
			filevardef(fout, "sfctemp", typeof(var), getvardims(var))
			fout->sfctemp = var
			continue
		end if		

		if (params(i) .eq. "sfcdewpt") then
			var = createRASPVar_float_XY(td2, "Surface Temperature (2m AGL)", "C")
			filevardef(fout, "sfcdewpt", typeof(var), getvardims(var))
			fout->sfcdewpt = var
			continue
		end if		

		if (params(i) .eq. "dbl") then
			var = createRASPVar_float_XY(pblh, "BL Depth", "m")
			filevardef(fout, "dbl", typeof(var), getvardims(var))
			fout->dbl = var
			continue
		end if		

		if (params(i) .eq. "sfcsun") then
			sfcsunVar = sfcsun(swdown)
			var = createRASPVar_float_XY(sfcsunVar, "Sfc. Solar Radiation", "")
			filevardef(fout, "sfcsun", typeof(var), getvardims(var))
			fout->sfcsun = var
			continue
		end if		

		if (params(i).eq."sfcsunpct") then
			; get time in YYYYMMDDHHmmss
			times = wrf_times_c(f->Times, 2)
			temp = times(0)
			year = doubletoint(temp / 10000000000.0)
			temp = temp  - (todouble(year) * 10000000000.0)
			month = doubletoint(temp / 100000000.0)
			temp = temp - (todouble(month) * 100000000.0)
			day = doubletoint(temp / 1000000.0)
			temp = temp - (todouble(day) * 1000000.0)
			hours = doubletoint(temp / 10000.0)
			temp = temp - (todouble(hours) * 10000.0)
			minutes = doubletoint(temp / 100.0)
			temp = temp - (todouble(minutes) * 100.0)
			seconds = doubletoint(temp)
			delete(temp)
			
			julianDayYear = greg2jul(year, month, day, hours) - greg2jul(year, 1, 1, hours) + 1
			hourFraction = tofloat(hours) + (tofloat(minutes) + (tofloat(seconds) / 60.0)) / 60.0
			
			sfcsunpctVar = sfcsunpct(toint(julianDayYear), hourFraction, swdown, pmb, tc, qvapor, nx, ny, nz, ter, z, alat, alon)
			var = createRASPVar_float_XY(sfcsunpctVar, "Normalized Sfc. Solar Radiation", "%")
			filevardef(fout, "sfcsunpct", typeof(var), getvardims(var))
			fout->sfcsunpct = var
			continue
		end if		

		if (params(i) .eq. "dwcrit") then
			if (.not. isvar("wstarVar")) then
				wstarVar = wstar(nx, ny, nz, vhf, pblh, hfx, tc)
			end if
			dwcritVar = dwcrit(wstarVar, ter, pblh, nx, ny)
			var = createRASPVar_float_XY(dwcritVar, "Depth of Critical Updraft Strength (AGL Hcrit)", "m")
			filevardef(fout, "dwcrit", typeof(var), getvardims(var))
			fout->dwcrit = var
			continue
		end if	
		
		if (params(i) .eq. "blcwbase") then
			blcwbaseVar = blcwbase( qcloud, z, ter, pblh, nx, ny, nz)
			var = createRASPVar_float_XY(blcwbaseVar, "BL Explicit Cloud Base [AGL] (CloudWater>" + cwbasecriteria + ")", "m")
			filevardef(fout, "blcwbase", typeof(var), getvardims(var))
			fout->blcwbase = var
			continue
		end if		
		
	end do
end