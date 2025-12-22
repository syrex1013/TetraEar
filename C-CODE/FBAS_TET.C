/************************************************************************
*
*	FILENAME		:	fbas_tet.c
*
*	DESCRIPTION		:	Library of basic functions used in the TETRA speech
*					codec, other than accepted operators
*
************************************************************************
*
*	FUNCTIONS		:	- add_sh()
*					- add_sh16()
*					- bin2int()
*					- int2bin()
*					- Load_sh()
*					- Load_sh16()
*					- norm_v()
*					- store _hi()
*					- sub_sh()
*					- sub_sh16()
*
************************************************************************
*
*	INCLUDED FILES	:	source.h
*
************************************************************************/

#include "source.h"

static Word16 POW2[16] = { -1, -2, -4, -8, -16, -32, -64, -128, -256, -512,
                           -1024, -2048, -4096, -8192, -16384, -32768};

/************************************************************************
*
*	Function Name : add_sh
*
*	Purpose :
*
*		Add var1 with a left shift(0-15) to L_var2.
*		Control saturation and set overflow flag 
*
*	Complexity Weight : 1
*
*	Inputs :
*
*		L_var2
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var2 <= 0x7fff ffff.
*
*		var1
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0xffff 8000 <= var1 <= 0x0000 7fff.
*
*		shift
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0 <= shift <= 15.
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var_out <= 0x7fff ffff.
*
************************************************************************/

Word32 add_sh(Word32 L_var2, Word16 var1, Word16 shift)
{
	return( L_msu0(L_var2, var1, POW2[shift]));
}


/************************************************************************
*
*	Function Name : add_sh16
*
*	Purpose :
*
*		Add var1 with a left shift of 16 to L_var2.
*		Control saturation and set overflow flag 
*
*	Complexity Weight : 1
*
*	Inputs :
*
*		L_var2
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var2 <= 0x7fff ffff.
*
*		var1
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0xffff 8000 <= var1 <= 0x0000 7fff.
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var_out <= 0x7fff ffff.
*
************************************************************************/

Word32 add_sh16(Word32 L_var2, Word16 var1)
{
	return( L_msu(L_var2, var1, (Word16)-32768));
}


/************************************************************************
*
*	Function Name : bin2int
*
*	Purpose :
*
*		Read "no_of_bits" bits from the array bitstream[] and convert to integer 
*
*	Inputs :
*
*		no_of_bits
*			16 bit 
*
*		*bitstream
*			16 bit 
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		value
*			32 bit 
*
************************************************************************/

#define BIT_1  1

Word16 bin2int(Word16 no_of_bits, Word16 *bitstream)
{
   Word16 value, i, bit;

   value = 0;
   for (i = 0; i < no_of_bits; i++)
   {
     value = shl( value,(Word16)1 );
     bit = *bitstream++;
     if (bit == BIT_1)  value += 1;
   }
   return(value);
}

/************************************************************************
*
*	Function Name : int2bin
*
*	Purpose :
*
*		Convert integer to binary and write the bits to the array bitstream [] 
*
*	Inputs :
*
*		no_of_bits
*			16 bit 
*
*		*bitstream
*			16 bit 
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		value
*			32 bit 
*
************************************************************************/

#define BIT_0     0
#define BIT_1     1
#define MASK      1

void int2bin(Word16 value, Word16 no_of_bits, Word16 *bitstream)
{
   Word16 *pt_bitstream, i, bit;

   pt_bitstream = bitstream + no_of_bits;

   for (i = 0; i < no_of_bits; i++)
   {
     bit = value & MASK;
     if (bit == 0)
         *--pt_bitstream = BIT_0;
     else
         *--pt_bitstream = BIT_1;
     value = shr( value,(Word16)1 );
   }
}


/************************************************************************
*
*	Function Name : Load_sh
*
*	Purpose :
*
*		Load the 16 bit var1 left shift(0-15) into the 32 bit output.
*		MS bits of the output are sign extended.
*
*	Complexity Weight : 1
*
*	Inputs :
*
*		var1
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0xffff 8000 <= var1 <= 0x0000 7fff.
*
*		shift
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0 <= var1 <= 15.
*
*	Outputs :
*
*		none.
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var_out <= 0x7fff ffff.
*
************************************************************************/

Word32 Load_sh(Word16 var1, Word16 shift)
{
	return( L_msu0( (Word32)0, var1, POW2[shift]));
}


/************************************************************************
*
*	Function Name : Load_sh16
*
*	Purpose :
*
*		Load the 16 bit var1 with a left shift of 16 into the 32 bit output.
*
*	Complexity Weight : 1
*
*	Inputs :
*
*		var1
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0xffff 8000 <= var1 <= 0x0000 7fff.
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var_out <= 0x7fff ffff.
*
************************************************************************/

Word32 Load_sh16(Word16 var1)
{
	return( L_msu( (Word32)0, var1, (Word16)-32768));
}


/************************************************************************
*
*	Function Name : norm_v
*
*	Purpose :
*
*		Variable normalisation of a 32 bit integer (L_var3).
*		var1 gives the maximum number of left shift to be done
*		*var2 returns the actual number of left shift 
*
*	Complexity Weight : 37
*
*	Inputs :
*
*		L_var3
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var3 <= 0x7fff ffff.
*
*		var1
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0 <= var1 <= 15.
*
*	Outputs :
*
*		*var2
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0 <= *var2 <= 15.
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var_out <= 0x7fff ffff.
*
************************************************************************/

Word32 norm_v(Word32 L_var3, Word16 var1, Word16 *var2)
  {
   Word16 shift;

   shift = norm_l(L_var3);
   if(sub(shift, var1) > 0) shift = var1;
   *var2 = shift;
   return(L_shl(L_var3, shift));
  }


/************************************************************************
*
*	Function Name : store_hi
*
*	Purpose :
*
*		Store high part of a L_var1 with a left shift of var2.
*
*	Complexity Weight : 3
*
*	Inputs :
*
*		L_var1
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var1 <= 0x7fff ffff.
*
*		var2
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0 <= var2 <= 7.
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		var_out
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0xffff 8000 <= var_out <= 0x0000 7fff.
*
************************************************************************/

Word16 store_hi(Word32 L_var1, Word16 var2)
{
  static Word16 SHR[8]={16, 15, 14, 13, 12, 11, 10, 9};
  return(extract_l( L_shr(L_var1, SHR[var2])));
}


/************************************************************************
*
*	Function Name : sub_sh
*
*	Purpose :
*
*		Subtract var1 with a left shift(0-15) to L_var2.
*		Control saturation and set overflow_flag.
*
*	Complexity Weight : 1
*
*	Inputs :
*
*		L_var2
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var2 <= 0x7fff ffff.
*
*		var1
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0xffff 8000 <= var1 <= 0x0000 7fff.
*
*		shift
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0 <= shift <= 15.
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var_out <= 0x7fff ffff.
*
************************************************************************/

Word32 sub_sh(Word32 L_var2, Word16 var1, Word16 shift)
{
	return( L_mac0(L_var2, var1, POW2[shift]));
}


/************************************************************************
*
*	Function Name : sub_sh16
*
*	Purpose :
*
*		Subtract var1 with a left shift of 16 to L_var2.
*		Control saturation and set overflow flag. 
*
*	Complexity Weight : 1
*
*	Inputs :
*
*		L_var2
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var2 <= 0x7fff ffff.
*
*		var1
*			16 bit short signed integer (Word16) whose value falls in the
*			range : 0xffff 8000 <= var1 <= 0x0000 7fff.
*
*	Outputs :
*
*		none
*
*	Returned Value :
*
*		L_var_out
*			32 bit long signed integer (Word32) whose value falls in the
*			range : 0x8000 0000 <= L_var_out <= 0x7fff ffff.

************************************************************************/

Word32 sub_sh16(Word32 L_var2, Word16 var1)
{
	return( L_mac(L_var2, var1, (Word16)-32768));
}

