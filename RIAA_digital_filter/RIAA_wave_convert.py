
import numpy as np
import math
import sys
from datetime import datetime
from datetime import timedelta


from RIAA_digital_filter.riaa_classes import InOutStream, RiaaFilter

if __name__== "__main__":
    if len(sys.argv) < 2:
        print("USAGE: RIAA_wave_convert.py filename [ku] [path]")
        sys.exit(1)

    fn = sys.argv[1]
    ku = float(sys.argv[2]) if len(sys.argv) > 2 else 16.0
    path = sys.argv[3] + "\\" if len(sys.argv) > 3 else ""

    io_stream = InOutStream(fn, ku, path)


print("Начинаем обработку файла:   ", io_stream.src_file)
print("частота дискретизации   :   ", io_stream.framerate/1000)
print("Разрядность             :   ", io_stream.params.sampwidth*8)
print("Количество каналов      :   ", io_stream.params.nchannels)
print("Длительность            :   ", timedelta(seconds =  io_stream.params.nframes/io_stream.framerate))
print("Время начала            :   ", datetime.now().time())

left_filter = RiaaFilter(io_stream.framerate)
right_filter = RiaaFilter(io_stream.framerate) if io_stream.params.nchannels > 1 else None

i=0
while True:

    samples = io_stream.get_readout()
    if samples.size == 0:
        break

    processed = np.zeros_like(samples)
    processed[:, 0] = left_filter.process(samples[:, 0])
    if right_filter:
        processed[:, 1] = right_filter.process(samples[:, 1])

    io_stream.put_readout(processed)

    if  i % int(io_stream.params.framerate * 10 / io_stream.buffer_size) == 0:
        print(f"\r{int(i * io_stream.buffer_size / io_stream.params.nframes * 100)}%  {datetime.now().time()}", end='', flush=True)
    i+=1


io_stream.close_all()
print("\nЗакончено в             :   ", datetime.now().time())
print("Left peak level     :  %f.2 dB" % (20 * math.log10(io_stream.ku*left_filter.peak_level/io_stream.level_0db)))
print("Right peak level    :  %f.2 dB" % (20 * math.log10(io_stream.ku*right_filter.peak_level/io_stream.level_0db)))
print("Left RMS level      :  %f.2 dB" % (20 * math.log10(io_stream.ku*math.sqrt(left_filter.rms_level/io_stream.params.nframes)/io_stream.level_0db)))
print("Right RMS level     :  %f.2 dB" % (20 * math.log10(io_stream.ku*math.sqrt(right_filter.rms_level/io_stream.params.nframes)/io_stream.level_0db)))