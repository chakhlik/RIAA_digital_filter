import wave
import math
from datetime import datetime

src = wave.open("multitone.wav", mode="r")
srcparam = src.getparams()
print(srcparam)

# main RIAA constants
tau_318 = 318e-6
tau_3180 = 3180e-6
tau_75 = 75e-6
T_sample = 1.0 / float(srcparam.framerate)

# coefs for 20-2000 Hz part
beta_1 = tau_318 / T_sample
alfa_1 = tau_3180 / T_sample
alfa_2 = tau_75 / T_sample

b0 = (1.0 + beta_1) / (1.0 + alfa_1 + alfa_2)
b1 = 1.0 / (1.0 + alfa_1 + alfa_2)
b2 = -1.0 * beta_1 / (1.0 + alfa_1 + alfa_2)
a1 = -1.0 / (1.0 + alfa_1 + alfa_2)  # changed sign
a2 = 1.0 * (alfa_1 + alfa_2) / (1 + alfa_1 + alfa_2)  # changed sign

coefs1 = [b0, b1, b2, a1, a2]
print(coefs1)

right_step_one = [0.0, 0.0, 0.0, 0.0]  # X0, X1, X2, Y1, Y2
left__step_one = [0.0, 0.0, 0.0, 0.0]

# coefs for 2000 - 22000 Hz part
f_tau_75 = 1 / (2 * math.pi * tau_75)
k = math.tan(math.pi * f_tau_75 / float(srcparam.framerate))
b = k / (k + 1.0)
a = -1.0 * (k - 1.0) / (k + 1.0)  # changed sign
coefs2 = [b, b, a]
right_step_two = [0.0, 0.0]
left__step_two = [0.0, 0.0]

dest = wave.open("multitone - SDFx.wav", mode="w")
dest.setparams(srcparam)

for i in range(0, srcparam.nframes):
    buf = src.readframes(1)
    # print(buf.hex(' ',3))

    left__step_one.insert(0, float(int.from_bytes(buf[0:3], 'little', signed=True)))
    right_step_one.insert(0, float(int.from_bytes(buf[3:6], 'little', signed=True)))

    # yl0 = math.sumprod(coefs, left__chan) #b0*xl0 + b1*xl1 + b2*xl2 - a1*yl1 - a2*yl2
    # yr0 = math.sumprod(coefs, right_chan) #b0*xr0 + b1*xr1 + b2*xr2 - a1*yr1 - a2*yr2
    yl0 = math.fsum([coefs1[0] * left__step_one[0], coefs1[1] * left__step_one[1], coefs1[2] * left__step_one[2],
                     coefs1[3] * left__step_one[3], coefs1[4] * left__step_one[4]])
    yr0 = math.fsum([coefs1[0] * right_step_one[0], coefs1[1] * right_step_one[1], coefs1[2] * right_step_one[2],
                     coefs1[3] * right_step_one[3], coefs1[4] * right_step_one[4]])

    if i < 2:
        yl0 = 0.0
        yr0 = 0.0

    left__step_one.insert(3, yl0)
    left__step_one.pop(2)
    left__step_one.pop(4)
    right_step_one.insert(3, yr0)
    right_step_one.pop(2)
    right_step_one.pop(4)

    left__step_two.insert(0, yl0)
    right_step_two.insert(0, yr0)

    yl1 = math.fsum([coefs2[0] * left__step_two[0], coefs2[1] * left__step_two[1], coefs2[2] * left__step_two[2]])
    yr1 = math.fsum([coefs2[0] * right_step_two[0], coefs2[1] * right_step_two[1], coefs2[2] * right_step_two[2]])

    yl = int(round(yl1 * 16.0, 0)).to_bytes(4, 'little', signed=True)[0:3]
    yr = int(round(yr1 * 16.0, 0)).to_bytes(4, 'little', signed=True)[0:3]
    # print(yl,'--',yr)
    buf_out = b''.join([yl, yr])
    # print(buf_out)
    dest.writeframesraw(buf_out)

    left__step_two.insert(2, yl1)
    left__step_two.pop(1)
    left__step_two.pop(2)
    right_step_two.insert(2, yr1)
    right_step_two.pop(1)
    right_step_two.pop(2)

    if i % (srcparam.framerate * 10) == 0:
        print(int(i / srcparam.nframes * 100), ' %   ', datetime.now().time())

src.close()
dest.close()
print('finished')
