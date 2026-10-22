cd /tmp/mirage
T=("" "Sequin Harbour" "Neon Tide Pull" "Kalahari Footsteps" "Quiet Signal" "Glass Coastline" "Mango Skies" "Rooftop Telegram" "Golden Chorus Line" "Concrete Sunrise" "Endless July")
ST=("" disco nudisco afro deep melodic tropical house vocal tech progressive)
CR=("" "Sean Oulashin" "llxvisuals" "Onofre Quezada" "Wendi Wells" "Armand Mckenzie" "Ittemaldiviano" "Vivek Panwar" "Yegor Denisov" "Geio Tischler" "Jared Rice")
for i in 2 3 4 5 6 7 8 9 10; do
  n=$(printf %02d $i)
  if [ $((i % 2)) -eq 0 ]; then S=/home/claude/videosyndication/mirage/video_short.py; o=out/${n}s.mp4; else S=/home/claude/videosyndication/mirage/video.py; o=out/${n}v.mp4; fi
  [ -f $o ] && continue
  python3 $S --image photos/$n.jpg --audio out/$n.delivery.wav --aac out/$n.m4a --title "${T[$i]}" --style ${ST[$i]} --credit "Photo: ${CR[$i]} / Unsplash" --out $o.tmp.mp4 && mv $o.tmp.mp4 $o && rm -rf $o.tmp.mp4.work
  echo "done $o $(date +%T)"
done
