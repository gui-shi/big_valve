$extension = ".mkv"

foreach($f in Get-Item "*$extension") {
    $pure = $f.Name.Replace($extension, "")
    ffmpeg -i $f.Name -vf "select='eq(pict_type,I)'" -vsync vfr "./pic/$($pure)_%03d.png"
}