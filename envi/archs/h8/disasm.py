import sys
import struct
import traceback

import envi
import envi.bits as e_bits

from envi.bits import binary
from const import *
from envi.archs.h8.regs import *

'''
mov b/w/l
movfpe b
movtpe b
pop  w/l
push w/l
--
add/sub b/w/l   add.b, add.w, add.l
addx/subx b
inc/dec b/w/l
adds/subs l
daa/das b
mulxs b/w
mulxu b/w
divxs b/w
divxu b/w
cmp b/w/l
neg b/w/l
exts w/l
extu w/l
and b/w/l
or  b/w/l
xor b/w/l
not b/w/l
--
shal/shar b/w/l
shll/shlr b/w/l
rotl/rotr b/w/l
rotxl/rotxr b/w/l
bset b
bclr b
bnot b
btst b
bad b
biand b
--
bor b
bior b
bxor b
bixor b
bld b
bild b
bst b
bist b
--
bcc bra/bt brn/bf bhi bls bhs bcs/blo bne beq bvc bvs bpl bmi bge blt bgt ble
jmp
bsr
jsr
rts
--
trapa
rte
sleep
ldc b/w
stc b/w
andc b
orc b
xorc b
nop
--
eepmov.b
eepmov.w

Eight addressing modes
    Register direct [Rn]
    Register indirect [@ERn]
    Register indirect with displacement [@(d:16,ERn) or @(d:24,ERn)]
    Register indirect with post-increment or pre-decrement [@ERn+ or @-ERn]
    Absolute address [@aa:8, @aa:16, or @aa:24]
    Immediate [#xx:8, #xx:16, or #xx:32]
    Program-counter relative [@(d:8,PC) or @(d:16,PC)]
    Memory indirect [@@aa:8]

'''
def addrToName(mcanv, va):
    sym = mcanv.syms.getSymByAddr(va)
    if sym != None:
        return repr(sym)
    return "0x%x" % va

class H8Opcode(envi.Opcode):
    _def_arch = envi.ARCH_H8
    def __hash__(self):
        return int(hash(self.mnem) ^ (self.size << 4))

    def __len__(self):
        return int(self.size)

    def getBranches(self, emu=None):
        """
        Return a list of tuples.  Each tuple contains the target VA of the
        branch, and a possible set of flags showing what type of branch it is.

        See the BR_FOO types for all the supported envi branch flags....
        Example: for bva,bflags in op.getBranches():
        """
        ret = []

        # FIXME: which do we use?  _def_arch?  or  & ARCH_MASK?
        brflags = (self.iflags & envi.ARCH_MASK) | self._def_arch

        # If we can fall through, reflect that...
        if not self.iflags & envi.IF_NOFALL:
            ret.append((self.va + self.size, brflags|envi.BR_FALL))

        # In H8, if we have no operands, it has no
        # further branches...
        if len(self.opers) == 0:
            return ret

        if self.iflags & envi.IF_COND:
            brflags |= envi.BR_COND

        if self.iflags & envi.IF_BRANCH:
            if self.opers[0].isDeref():
                brflags |= envi.BR_DEREF
            ret.append((self.getOperValue(0), brflags))

        elif self.iflags & envi.IF_CALL:
            brflags |= envi.BR_PROC
            if self.opers[0].isDeref():
                brflags |= envi.BR_DEREF
            ret.append((self.getOperValue(0), brflags))

        return ret

    def render(self, mcanv):
        """
        Render this opcode to the specified memory canvas
        """
        mnem = self.mnem
        if self.iflags & IF_B:
            mnem += '.b'
        elif self.iflags & IF_W:
            mnem += '.w'
        elif self.iflags & IF_L:
            mnem += '.l'

        mcanv.addNameText(mnem, typename="mnemonic")
        mcanv.addText(" ")

        # Allow each of our operands to render
        imax = len(self.opers)
        lasti = imax - 1
        for i in xrange(imax):
            oper = self.opers[i]
            oper.render(mcanv, self, i)
            if i != lasti:
                mcanv.addText(",")

    def __repr__(self):
        mnem = self.mnem
        if self.iflags & IF_B:
            mnem += '.b'
        elif self.iflags & IF_W:
            mnem += '.w'
        elif self.iflags & IF_L:
            mnem += '.l'
        
        x = []
        for o in self.opers:
            x.append(o.repr(self))

        return mnem + " " + ", ".join(x)



def unittest_parsers(buf = 'ABCDEFGHIJKLMNOP', off=3, va=0x2544):
    val, = struct.unpack('>H', buf[off:off+2])

    for tsize in (1,2,4):
        p_i3_Rd(va, val, buf, off, tsize)
        p_i3_aERd(va, val, buf, off, tsize) 
        p_i3_aAA8(va, val, buf, off, tsize) 
        p_i8_CCR(va, val, buf, off, tsize) 
        p_i8_Rd(va, val, buf, off, tsize) 
        p_i16_Rd(va, val, buf, off, tsize) 
        p_i32_ERd(va, val, buf, off, tsize) 
        p_Rd(va, val, buf, off, tsize) 
        p_Rs_Rd(va, val, buf, off, tsize)  
        p_Rs_Rd_4b(va, val, buf, off, tsize)  
        p_Rs_ERd(va, val, buf, off, tsize)  
        p_Rs_ERd_4b(va, val, buf, off, tsize)  
        p_ERd(va, val, buf, off, tsize)  
        p_ERs_ERd(va, val, buf, off, tsize)  
        p_Rn_Rd(va, val, buf, off, tsize)  
        p_Rn_aERd(va, val, buf, off, tsize)  
        p_Rn_aAA8(va, val, buf, off, tsize)  
        p_aERn(va, val, buf, off, tsize)  
        p_aAA24(va, val, buf, off, tsize)  
        p_aaAA8(va, val, buf, off, tsize)  
        p_1_Rd(va, val, buf, off, tsize)  
        p_2_Rd(va, val, buf, off, tsize)  
        p_4_Rd(va, val, buf, off, tsize)  
        p_1_ERd(va, val, buf, off, tsize)  
        p_2_ERd(va, val, buf, off, tsize)  
        p_4_ERd(va, val, buf, off, tsize)  
        p_disp8(va, val, buf, off, tsize)  
        p_dis16(va, val, buf, off, tsize)  
        p_nooperands(va, val, buf, off, tsize) 

class H8Operand(envi.Operand):
    tsize = 2
    def involvesPC(self):
        return False

class H8RegDirOper(envi.RegisterOper, H8Operand):
    ''' 
    Register direct [Rn]
    '''

    def __init__(self, reg, tsize=4, va=0, oflags=0):
        self.va = va
        self.reg = convertMeta(reg, tsize)
        self.tsize = tsize
        self.oflags = oflags

    def __eq__(self, oper):
        if not isinstance(oper, self.__class__):
            return False
        if self.reg != oper.reg:
            return False
        if self.tsize != oper.tsize:
            return False
        if self.oflags != oper.oflags:
            return False
        return True
    
    def involvesPC(self):
        return self.reg == REG_PC

    def isDeref(self):
        return False

    def getOperValue(self, op, emu=None):
        if self.reg == REG_PC:
            return self.va  # FIXME: is this modified?  or do we need to att # to this?

        if emu == None:
            return None
        return emu.getRegister(self.reg)

    def setOperValue(self, op, emu=None, val=None):
        if emu == None:
            return None
        emu.setRegister(self.reg, val)

    def render(self, mcanv, op, idx):
        name = self._dis_regctx.getRegisterName(self.reg)
        rname = self._dis_regctx.getRegisterName(self.reg&RMETA_NMASK)
        mcanv.addNameText(name, name=rname, typename="registers")

    def repr(self, op):
        name = self._dis_regctx.getRegisterName(self.reg)
        return name

class H8RegIndirOper(envi.DerefOper, H8Operand):
    '''
    Register Indirect
    register specifies 32bit ERn reg, lower 24bits being an address

    FIXME: some instructions use "@ERd" but seem to mean "ERd"??  check docs.
    Register indirect [@ERn]
    Register indirect with displacement [@(d:16,ERn) or @(d:24,ERn)]
    Register indirect with post-increment or pre-decrement [@ERn+ or @-ERn]
    '''

    def __init__(self, reg, tsize, va, disp=0, dispsz=0, oflags=0):
        self.va = va
        self.reg = reg
        self.disp = disp
        self.dispsz = 8 * dispsz
        self.tsize = tsize
        self.oflags = oflags

    def __eq__(self, oper):
        if not isinstance(oper, self.__class__):
            return False
        if self.reg != oper.reg:
            return False
        if self.disp != oper.disp:
            return False
        if self.oflags != oper.oflags:
            return False
        if self.dispsz != oper.dispsz:
            return False
        return True

    def involvesPC(self):
        return self.reg == REG_PC

    def isDeref(self):
        return True

    def getOperAddr(self, op, emu=None, mod=False):
        '''
        if mod==True, actually update the register for PostInc/PreDec
        '''
        addr = self.disp
        if self.oflags & OF_PREDEC:
            addr -= self.tsize

        if self.reg == REG_PC:
            addr += self.va
            return addr

        if emu == None:
            return None

        addr += emu.getRegister(self.reg)

        if mod:
            if self.oflags & OF_PREDEC:
                emu.setRegister(self.reg, emu.getRegister(self.reg) - self.tsize)
            elif self.oflags & OF_POSTINC:
                emu.setRegister(self.reg, emu.getRegister(self.reg) + self.tsize)

        return addr

    def getOperValue(self, op, emu=None, mod=False):
        if emu == None:
            return None
        addr = self.getOperAddr( op, emu, mod )
        return emu.readMemValue(addr, self.tsize)

    def setOperValue(self, op, emu=None, val=None, mod=True):
        if emu == None:
            return None
        
        addr = self.getOperAddr( op, emu, mod )
        emu.writeMemValue(addr, val, self.tsize)

    def render(self, mcanv, op, idx):
        name = self._dis_regctx.getRegisterName(self.reg)
        rname = self._dis_regctx.getRegisterName(self.reg&RMETA_NMASK)
        mcanv.addText('@')
        if self.disp:
            mcanv.addText('(0x%x:%d, ' % (self.disp, self.dispsz))
        if self.oflags & OF_PREDEC:
            mcanv.addText('-')
        mcanv.addNameText(name, name=rname, typename="registers")
        if self.oflags & OF_POSTINC:
            mcanv.addText('+')
        if self.disp:
            mcanv.addText(')')

    def repr(self, op):
        out = ['@']
        name = self._dis_regctx.getRegisterName(self.reg)
        rname = self._dis_regctx.getRegisterName(self.reg&RMETA_NMASK)
        if self.disp:
            out.append('(0x%x:%d, ' % (self.disp, self.dispsz))

        if self.oflags & OF_PREDEC:
            out.append('-')

        out.append(rname)

        if self.oflags & OF_POSTINC:
            out.append('+')

        if self.disp:
            out.append(')')
        return ''.join(out)

class H8RegMultiOper(H8Operand):
    '''
    Multiple Registers used by STM/LDM
    rn = upper register
    count = number of registers (2, 3, or 4)
    '''
    def __init__(self, basereg, count):
        self.count = count
        self.basereg = basereg

    def __eq__(self, oper):
        if not isinstance(oper, self.__class__):
            return False
        if self.basereg != oper.basereg:
            return False
        if self.count != oper.count:
            return False
        return True

    def involvesPC(self):
        return False

    def isDeref(self):
        return False

    def getOperValue(self, op, emu=None):
        return [self.basereg + x for x in range(self.count)]

    def render(self, mcanv, op, idx):
        basereg = self.basereg & RMETA_NMASK
        mcanv.addText('(')
        rname = self._dis_regctx.getRegisterName(self.basereg)
        mcanv.addNameText(rname, name=rname, typename="registers")
        mcanv.addText('-')
        rname = self._dis_regctx.getRegisterName(self.basereg + self.count - 1)
        mcanv.addNameText(rname, name=rname, typename="registers")
        mcanv.addText(')')

    def repr(self, op):
        basereg = self.basereg & RMETA_NMASK
        out = [ '(' ]

        rname = self._dis_regctx.getRegisterName(self.basereg)
        out.append(rname)
       
        out.append('-')
        rname = self._dis_regctx.getRegisterName(self.basereg + self.count - 1)
        out.append(rname)
        
        out.append(')')
        return ''.join(out)


class H8AbsAddrOper(H8Operand):
    '''
    Absolute address [@aa:8, @aa:16, or @aa:24]
    '''
    def __init__(self, aa, tsize=1, aasize=2):
        if aa & 0xffff00 == 0:
            aa |= 0xffff00

        self.aa = aa
        self.tsize = tsize
        self.aasize = 8 * aasize

    def __eq__(self, oper):
        if not isinstance(oper, self.__class__):
            return False
        if self.aa != oper.aa:
            return False
        if self.tsize != oper.tsize:
            return False
        return True

    def involvesPC(self):
        return False

    def isDeref(self):
        return False

    def getOperAddr(self, op, emu=None):
        return self.aa

    def getOperValue(self, op, emu=None):
        return self.aa

    def render(self, mcanv, op, idx):
        mcanv.addText('@')
        if mcanv.mem.isValidPointer(self.aa):
            name = addrToName(mcanv, self.aa)
            mcanv.addVaText(name, self.aa)
            mcanv.addText(':%d' % (self.aasize))
        else:
            aa = '0x%.4x:%d' % (self.aa, self.aasize)
            mcanv.addVaText(aa, self.aa)

    def repr(self, op):
        return '@0x%x:%d' % (self.aa, self.aasize)

class H8ImmOper(envi.ImmedOper, H8Operand):
    '''
    Immediate [#xx:8, #xx:16, or #xx:32]
    '''
    def __init__(self, val, tsize, oflags=0):
        self.val = val
        self.oflags = oflags
        self.tsize = tsize

    def __eq__(self, oper):
        if not isinstance(oper, self.__class__):
            return False
        if self.val != oper.val:
            return False
        if self.tsize != oper.tsize:
            return False
        return True

    def involvesPC(self):
        return False

    def isDeref(self):
        return False

    def getOperValue(self, op, emu=None):
        return self.val

    def render(self, mcanv, op, idx):
        mcanv.addText('#')
        if mcanv.mem.isValidPointer(self.val):
            if mcanv.mem.getName(self.val):
                name = addrToName(mcanv, self.val)
                mcanv.addVaText(name, self.val)
            else:
                mcanv.addVaText('0x%x' % self.val, self.val)
        else:
            mcanv.addNameText('0x%x' % self.val, typename='immediate')

    def repr(self, op):
        return "#%x" % self.val

class H8MemIndirOper(envi.DerefOper, H8Operand):
    '''
    Memory indirect [@@aa:8]
    '''
    def __init__(self, aa, tsize=1):
        self.aa = aa
        self.tsize = tsize

    def __eq__(self, oper):
        if not isinstance(oper, self.__class__):
            return False
        if self.aa != oper.aa:
            return False
        if self.tsize != oper.tsize:
            return False
        return True

    def involvesPC(self):
        return False

    def isDeref(self):
        return True

    def getOperValue(self, op, emu=None):
        # can't survive without an emulator
        if emu == None:
            return None

        addr = self.getOperAddr(op, emu)
        ret = emu.readMemoryValue(addr, self.tsize)
        return ret

    def getOperAddr(self, op, emu=None):
        return self.aa

    def getOperValue(self, op, emu=None):
        if emu == None:
            return 

        dsize = self.tsize
        val = emu.readMemoryValue(self.getOperAddr(op, emu), dsize)
        return val

    def render(self, mcanv, op, idx):
        mcanv.addText('@@')
        mcanv.addNameText('%x'%self.aa, name=self.aa, typename='address')

    def repr(self, op):
        return '@@%x' % self.aa

class H8PcOffsetOper(H8Operand):
    '''
    PC Relative Address

    H8ImmOper but for Branches, not a dereference.  perhaps we can have H8ImmOper do all the things... but for now we have this.
    Program-counter relative [@(d:8,PC) or @(d:16,PC)]
    '''
    def __init__(self, val, va, aasize):
        self.va = va
        self.val = val
        self.aasize = aasize

    def __eq__(self, oper):
        ''' unfixed '''
        if not isinstance(oper, self.__class__):
            return False
        if self.val != oper.val:
            return False
        if self.va != oper.va:
            return False
        if self.aasize != oper.aasize:
            return False
        return True

    def involvesPC(self):
        return True

    def isDeref(self):
        return False

    def isDiscrete(self):
        return False

    def getOperValue(self, op, emu=None):
        return len(op) + self.va + self.val

    def render(self, mcanv, op, idx):
        value = self.getOperValue(op)
        if mcanv.mem.isValidPointer(value):
            name = addrToName(mcanv, value)
            mcanv.addVaText(name, value)
            mcanv.addText(':%d' % (8 * self.aasize))
        else:
            mcanv.addVaText('%.4x:%d' % (value, 8 * self.aasize), value)

    def repr(self, op):
        targ = self.getOperValue(op)
        tname = "%.4x:%d" % (targ, 8 * self.aasize)
        return tname


from optables import main_table
class H8Disasm:
    fmt = ">H"

    def __init__(self):
        self._dis_regctx = H8RegisterContext()
        self._dis_oparch = envi.ARCH_H8
        self.ptrsize = 4

    def disasm(self, bytez, offset, va):
        """
        Parse a sequence of bytes out into an envi.Opcode instance.
        """
        opbytes = bytez[offset:offset+2]
        opval, = struct.unpack(">H", opbytes)

        prim = opval >> 8
        opdata = main_table[prim]

        if opdata == None:
            raise envi.InvalidInstruction(bytez=bytez[offset:offset+16], va=va)

        subtable, mnem, decoder, tsize, iflags = opdata

        if subtable:
            raise Exception("WHAT ARE WE DOING HERE.  NEED subtable at 0x%x:  %s" % (va, bytez[offset:offset+16].encode('hex')))

        elif decoder != None:
            opcode, nmnem, olist, flags, isize = decoder(va, opval, bytez, offset, tsize)
            #print opcode, nmnem, olist, flags, isize, decoder
            if nmnem != None:
                mnem = nmnem
            iflags |= flags

        else:
            opcode = opval
            isize = 2
            olist = tuple()
            #raise envi.InvalidInstruction(mesg='Failed to find subtable or decoder', bytez=bytez[offset:offset+16], va=va)

        if olist == None:
            raise envi.InvalidInstruction(mesg='Operand list cannot be None for instruction "%s"' % mnem, bytez=bytez[offset:offset+16], va=va)
        op = H8Opcode(va, opcode, mnem, None, isize, olist, iflags)

        if op.opers != None:
            # following the nasty little hack from other modules.  "everybody's doing it!"
            for oper in op.opers:
                oper._dis_regctx = self._dis_regctx

        return op

if __name__ == '__main__':
    import envi.archs
    envi.archs.dismain( H8Disasm() )
