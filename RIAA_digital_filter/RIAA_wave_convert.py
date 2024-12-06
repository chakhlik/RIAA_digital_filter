import sys
from datetime import datetime
from datetime import timedelta

from RIAA_digital_filter.riaa_classes import InOutStream, RiaaFilter

if __name__== "__main__":
    a=len(sys.argv)
    match a:
        case 1:
            print('USAGE : python command.py Filename [ku] [path]')
            sys.exit("no filename passed")
        case 2:
            fn = sys.argv[1]
            io_stream = InOutStream(fn)
        case 3:
            fn = sys.argv[1]
            ku = float(sys.argv[2])
            io_stream = InOutStream(fn, ku)
        case 4:
            fn = sys.argv[1]
            ku = float(sys.argv[2])
            path = sys.argv[3]
            io_stream = InOutStream(fn, ku, path+'\\')
        case _:
            print('USAGE : python command.py Filename [ku] [path]')
            sys.exit("wrong parameters")


print("Начинаем обработку файла:  ", io_stream.src_file)
print("частота дискретизации   :  ", io_stream.framerate/1000)
print("Разрядность             :  ", io_stream.params.sampwidth*8)
print("Количество каналов      :  ", io_stream.params.nchannels)
print("Длительность            :  ", timedelta(seconds =  io_stream.params.nframes/io_stream.framerate))

left = RiaaFilter(io_stream.framerate)
right = RiaaFilter(io_stream.framerate)
o_left = 0.0
o_right = 0.0

for i in range(0, io_stream.params.nframes):
    readings = io_stream.get_readout()
    o_left = left.process(readings[0])
    if io_stream.params.nchannels>1:
        o_right = right.process(readings[1])
    io_stream.put_readout(o_left, o_right)
    if i % (io_stream.params.framerate * 10) == 0:
        print(int(i / io_stream.params.nframes * 100), ' %   ', datetime.now().time())

io_stream.close_all()
print("Finished")

