;;; Open Workstation for head or side

function openWksHd(plot_param, tail)
begin
	if( FMT .eq. "png" ) then
		wks = create (OutDir + plot_param + tail + ".head") imageWorkstationClass defaultapp
                "wkHeight"          : wkHeight
                "wkWidth"           : wkWidth
                "wkBackgroundColor" : "white"
                "wkForegroundColor" : "black"
                "wkColorMap"        : "BlAqGrYeOrReVi200"      ; probably best by DrJack
		end create
	else
		if( FMT .eq. "svg" ) then
			wks = create (OutDir + plot_param + tail + ".head") imageWorkstationClass defaultapp
					"wkHeight"          : wkHeight
					"wkWidth"           : wkWidth
					"wkBackgroundColor" : "white"
					"wkForegroundColor" : "black"
					"wkColorMap"        : "BlAqGrYeOrReVi200"      ; probably best by DrJack
			end create
		end if
	end if
	return(wks)
end

function openWksLb(plot_param, tail, where)
begin
	if( FMT .eq. "png" ) then
		wks = create (OutDir + plot_param + tail + where) imageWorkstationClass defaultapp
			"wkHeight"          : wkHeight
			"wkWidth"           : wkWidth
			"wkBackgroundColor" : "white"
			"wkForegroundColor" : "black"
			"wkColorMap"        : "BlAqGrYeOrReVi200"      ; probably best by DrJack
		end create
	else
		if( FMT .eq. "svg" ) then
			wks = create (OutDir + plot_param + tail + where) imageWorkstationClass defaultapp
				"wkHeight"          : wkHeight
				"wkWidth"           : wkWidth
				"wkBackgroundColor" : "white"
				"wkForegroundColor" : "black"
				"wkColorMap"        : "BlAqGrYeOrReVi200"      ; probably best by DrJack
			end create
		end if
	end if
	return(wks)
end

