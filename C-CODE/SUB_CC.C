/************************************************************************
*	FILENAME		:	sub_cc.c
*
*	DESCRIPTION		:	Sub-routines for speech channel encoding
*
************************************************************************
*
*	SUBROUTINES		:	- Build_Crc()
*					- Build_Sensitivity_Classes()
*					- Combination()
*					- Init_Rcpc_Coding()
*					- Interleaving_Signalling()
*					- Interleaving_Speech()
*					- Rcpc_Coding()
*					- Transform_Class_0()
*					- Write_Tetra_File()
*
************************************************************************
*
*	INCLUDED FILES	:	arrays.tab
*					channel.h
*					const.tab
*					stdlib.h
*
************************************************************************/

#include <stdlib.h>
#include "channel.h"
#include "const.tab" /* contains constants for channel coding/decoding */
#include "arrays.tab" /* contains arrays for channel coding/decoding */

/* #define DEBUG */	   /*	This is a compilation directive eventually used
					in the routine Rcpc_Coding to check that the
					puncturing matrices A1 and A2 are correctly set

					The results given by this software shall be the
					same, independently of the definition of DEBUG

					The complexity of the channel encoding
					component has been evaluated with the
					assumption that DEBUG is NOT defined */

/**************************************************************************
*
*	ROUTINE				:	Build_Crc
*
*	DESCRIPTION			:	Computation of a 8 bit CRC and concatenation
*							to the input frame
*
**************************************************************************
*
*	USAGE				:	Build_Crc(flag,buffer)
*							(Routine_Name(arg1,arg2))
*
*	ARGUMENT(S)			:	
*
*		ARG1				:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*						- Format : Word16**		ARG2				:	- Description : input serial stream containing*						parameters of 2 speech frames re-ordered in 3 *						sensitivity classes*							- Format : **	RETURNED VALUE		:	None**	COMMENTS			:	8 bit CRC is computed on the third sensitivity class***************************************************************************/Word16     Build_Crc(Word16 FS_Flag, Word16 Input_Frame[])
{
/* Variables */
Word16             i, temp;


if (!FS_Flag) {

	/* The class protected by the CRC (Class 2) starts at index N0_2 + N1_2 */
	/* First Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC1; i++)
	  temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC1[i] - 1]);
	/* The CRC bit is the LSB of temp : */
	temp = temp & 1;
	/* Concatenation of the CRC bit to Input_Frame : */
	Input_Frame[N0_2 + N1_2 + N2_2] = temp;

	/* Second Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC2; i++)
	  temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC2[i] - 1]);
	temp = temp & 1;
	Input_Frame[N0_2 + N1_2 + N2_2 + 1] = temp;

	/* Third Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC3; i++)
	  temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC3[i] - 1]);
	temp = temp & 1;
	Input_Frame[N0_2 + N1_2 + N2_2 + 2] = temp;


	/* Fourth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC4; i++)
	  temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC4[i] - 1]);
	temp = temp & 1; 
	Input_Frame[N0_2 + N1_2 + N2_2 + 3] = temp;

	/* Fifth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC5; i++)
	  temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC5[i] - 1]);
	temp = temp & 1; 
	Input_Frame[N0_2 + N1_2 + N2_2 + 4] = temp;

	/* Sixth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC6; i++)
	  temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC6[i] - 1]);
	temp = temp & 1; 
	Input_Frame[N0_2 + N1_2 + N2_2 + 5] = temp;

	/* Seventh Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC7; i++)
	  temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC7[i] - 1]);
	temp = temp & 1;   
	Input_Frame[N0_2 + N1_2 + N2_2 + 6] = temp;

	/* Eighth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC8; i++)
	  temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC8[i] - 1]);
	temp = temp & 1;  
	Input_Frame[N0_2 + N1_2 + N2_2 + 7] = temp;

	return(0);
} /* If !FS_Flag */
else {
	/* The class protected by the CRC (Class 2) starts at index N0 + N1 */
	
	/* First Bit of the CRC : */
	temp = 0;
	for (i = 0; i < Fs_SIZE_TAB_CRC1; i++)
	  temp = add(temp,Input_Frame[N0 + N1 + Fs_TAB_CRC1[i] - 1]);
	/* The CRC bit is the LSB of temp : */
	temp = temp & 1;
	/* Concatenation of the CRC bit to Input_Frame : */
	Input_Frame[N0 + N1 + N2] = temp;

	/* Second Bit of the CRC : */
	temp = 0;
	for (i = 0; i < Fs_SIZE_TAB_CRC2; i++)
	  temp = add(temp,Input_Frame[N0 + N1 + Fs_TAB_CRC2[i] - 1]);
	temp = temp & 1;
	Input_Frame[N0 + N1 + N2 + 1] = temp;

	/* Third Bit of the CRC : */
	temp = 0;
	for (i = 0; i < Fs_SIZE_TAB_CRC3; i++)
	  temp = add(temp,Input_Frame[N0 + N1 + Fs_TAB_CRC3[i] - 1]);
	temp = temp & 1;
	Input_Frame[N0 + N1 + N2 + 2] = temp;

	/* Fourth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < Fs_SIZE_TAB_CRC4; i++)
	  temp = add(temp,Input_Frame[N0 + N1 + Fs_TAB_CRC4[i] - 1]);
	temp = temp & 1; 
	Input_Frame[N0 + N1 + N2 + 3] = temp;
	return(0);
}
}
/**************************************************************************
*
*	ROUTINE				:	Build_Sensitivity_Classes
*
*	DESCRIPTION			:	Reorders two concatened speech frames into a single
*						frame ordered in three sensitivity classes 
*						(from least, ie Class 0, to most sensitive bits, 
*						ie Class 2)
*
**************************************************************************
*
*	USAGE				:	Build_Sensitivity_Classes(flag,buffer_in, buffer_out)
*							(Routine_Name(input1,input2,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*							- Format : Word16**		INPUT2			:	- Description : 2 concatenated speech frames*							- Format : 274 * 16 bit-samples**	OUTPUT ARGUMENT(S)		:	**		OUTPUT1			:	- Description : 1 reordered frame*							- Format : 274 * 16 bit-samples**	RETURNED VALUE		:	None***************************************************************************/Word16     Build_Sensitivity_Classes(Word16 FS_Flag, Word16 Input_Frame[], Word16 Output_Frame[])
{
/* Variables */
Word16             i;

if (!FS_Flag) {
	/* Class 0 : */
	for (i = 0; i < N0; i++) {
	       Output_Frame[2*i] = Input_Frame[TAB0[i] - 1];
	       Output_Frame[2*i + 1] = Input_Frame[Length_vocoder_frame + TAB0[i] - 1];
	}

	/* Building and Concatenation of Class 1 : */
	for (i = 0; i < N1; i++) {
	       Output_Frame[2*(N0 + i)] = Input_Frame[TAB1[i] - 1];
	       Output_Frame[2*(N0 + i) + 1] = Input_Frame[Length_vocoder_frame + TAB1[i] - 1];
	}

	/* Building and Concatenation of Class 2 : */
	for (i = 0; i < N2; i++) {
	       Output_Frame[2*(N0 + N1 + i)] = Input_Frame[TAB2[i] - 1];
	       Output_Frame[2*(N0 + N1 + i) + 1] = Input_Frame[Length_vocoder_frame + TAB2[i] - 1];
	}

	return(0);

} /* If !FS_Flag */

else {
	/* Class 0 : */
	for (i = 0; i < N0; i++)
		Output_Frame[i] = Input_Frame[TAB0[i] - 1];

	/* Building and Concatenation of Class 1 : */
	for (i = 0; i < N1; i++)
		Output_Frame[N0 + i] = Input_Frame[TAB1[i] - 1];

	/* Building and Concatenation of Class 2 : */
	for (i = 0; i < N2; i++)
		Output_Frame[N0 + N1 + i] = Input_Frame[TAB2[i] - 1];

	return(0);
}

}


/**************************************************************************
*
*	ROUTINE				:	Combination
*
*	DESCRIPTION			:	Computes the (convolutional) coded bit for a given
*							polynomial generator and a given state of the encoder
*
**************************************************************************
*
*	USAGE				:	Combination(gene,state)
*							(Routine_Name(input1,input2))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Polynomial generator
*							- Format : Word16 
*
*		INPUT2			:	- Description : State of the encoder
*							- Format : Word16
*
*	RETURNED VALUE		:	1 coded bit
*
**************************************************************************/

Word16     Combination(Word16 A, Word16 B)
{
Word16             Comb;
Word16             i, temp1, temp2, temp3;

      Comb = -1;
      temp1 = A & B;

      for (i = 0;i <= (K - 1);i++)
	  {
	  temp2 = shl( (Word16)1,i );
	  temp3 = temp1 & temp2;
	  if (temp3 != 0) Comb = negate(Comb);
	  }
      return(Comb);

}

/**************************************************************************
*
*	ROUTINE				:	Init_Rcpc_Coding
*
*	DESCRIPTION			:	Initialization for channel encoding
*
**************************************************************************
*
*	USAGE				:	Init_Rcpc_Coding(flag,buffer)
*							(Routine_Name(arg1,arg2))
*
*	ARGUMENT(S)			:
*
*		ARG1				:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*						- Format : Word16**		ARG2				:	- Description : Frame to be encoded*							- Format : 286 * 16 bit-samples**	RETURNED VALUE		:	None**	COMMENTS			:	4 zeroes are concatenated to the input buffer*							to clear the encoder ***************************************************************************/

void	Init_Rcpc_Coding(Word16 FS_Flag, Word16 Input_Frame[])
{
/* Variables */ 
Word16             i, M;
Word16             Arrival_state;  /* index for Loop on the Lattice States */
Word16             Starting_state;
Word16             Msb;    /* Value used for computation of coded bit */
Word16             Lsb;    /* Value used for computation of coded bit */
Word16             Lsb_bits;
Word16             Msbs_starting_state;
Word16             Involved_bits;

if (!FS_Flag) {

	/* Initialization of Nber_Info_Bits, number of bits to be encoded :
	-       Class 1, N1_2 bits,
	-       Class 2, N2_2 bits,
	-       CRC bits
	-       (K - 1) zeros to empty the encoder */
	Nber_Info_Bits = N1_2 + N2_2 + SIZE_CRC;
	/* Zero the (K - 1) last bits of the Input_Frame */
	for (i = 0; i < K - 1; i++) {
		Input_Frame[N0_2 + Nber_Info_Bits] = 0;
		Nber_Info_Bits++;
		}
	/* Nber_Info_Bits = N1_2 + N2_2 + SIZE_CRC + (K - 1) */
} /* If FS_Flag */

else {
	
	/* Initialization of Nber_Info_Bits, number of bits to be encoded :
	-       Class 1, N1 bits,
	-       Class 2, N2 bits,
	-       Fs_CRC bits
	-       (K - 1) zeros to empty the encoder */
	Nber_Info_Bits = N1 + N2 + Fs_SIZE_CRC;
	/* Zero the (K - 1) last bits of the Input_Frame */
	for (i = 0; i < K - 1; i++) {
		Input_Frame[N0 + Nber_Info_Bits] = 0;
		Nber_Info_Bits++;
		}
	/* Nber_Info_Bits = N1 + N2 + Fs_SIZE_CRC + (K - 1) */

}

/* Number of states in the Viterbi Lattice : */
M = shl( (Word16)1,(Word16)(K - 1) );
/* Last State of the Viterbi Lattice */
M_1 = sub( M,(Word16)1 ); 

Msb_bit = shl( (Word16)1,(Word16)(K - 2) );
Lsb_bits = Msb_bit - 1;


/* Description of the Lattice : Loop on Arrival_State */
for (Arrival_state = 0; Arrival_state <= M_1; Arrival_state++) {
/* Computation of the MSB for the Arrival State */
	Msb = Arrival_state & Msb_bit;
/* Computation of the (K - 1)MSBs for the Starting State */
	Msbs_starting_state = Arrival_state & Lsb_bits;
	
/* Loop on Lsb, LSB of the Starting State */
	for (Lsb = 0; Lsb <= 1; Lsb++) {
		Starting_state = add( shl( Msbs_starting_state,(Word16)1 ),Lsb );
		Previous[Arrival_state][Lsb] = Starting_state;
/*   TRANSITION BITS T1, T2, T3   */
		Involved_bits = add(shl( Msb,(Word16)1 ),Starting_state);

		T1[Arrival_state][Lsb] = Combination( Involved_bits,(Word16)G1 );
		T2[Arrival_state][Lsb] = Combination( Involved_bits,(Word16)G2 );
		T3[Arrival_state][Lsb] = Combination( Involved_bits,(Word16)G3 );
	} /* End Loop on Lsb  */

} /* End Loop on Arrival_state */
}


/**************************************************************************
*
*	ROUTINE				:	Interleaving_Signalling
*
*	DESCRIPTION			:	Signalling channel-type interleaving
*							of a single frame (216 bits)
*
**************************************************************************
*
*	USAGE				:	Interleaving_Signalling(buffer_in,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Input buffer
*							- Format : 216 * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Interleaved buffer
*							- Format : 216 * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

Word16     Interleaving_Signalling(Word16 Input_Frame[],
			Word16 Output_frame[])
{
static Word16   K3_const = 216;
static Word16   K_const = 216;
static Word16   a_const = 101;
Word16  i, k;


for (i = 0; i < K3_const; i++) {
	k = (Word16)((Word32)((Word32)a_const * (Word32)(i+1)) % K_const);
	Output_frame[k] = Input_Frame[i];
}

return(0);
}

/**************************************************************************
*
*	ROUTINE				:	Interleaving_Speech
*
*	DESCRIPTION			:	Matrix interleaving of a  432 bits frame 
*
**************************************************************************
*
*	USAGE				:	Interleaving_Speech(buffer_in,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : Input buffer
*							- Format : 432 * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Interleaved buffer
*							- Format : 432 * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

Word16     Interleaving_Speech(Word16 Input_Frame[],
			Word16 Output_frame[])
{
Word16             index_lines, index_columns;

for (index_columns = 0; index_columns < COLUMNS; index_columns++) {
	  for (index_lines = 0; index_lines < LINES; index_lines++)
		Output_frame[index_columns * LINES + index_lines] =
			Input_Frame[index_lines * COLUMNS + index_columns];
} /* End Loop COLUMNS */

return(0);
}


/**************************************************************************
*
*	ROUTINE				:	Rcpc_Coding
*
*	DESCRIPTION			:	Routine for channel encoding
*
**************************************************************************
*
*	USAGE				:	Rcpc_Coding(flag,buffer_in,buffer_out)
*							(Routine_Name(input1,input2,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*						- Format : Word16**		INPUT2			:	- Description : Frame to be encoded*							- Format : 286 * 16 bit-samples**	OUTPUT ARGUMENT(S)		:	**		OUTPUT1			:	- Description : Encoded frame*							- Format : 432 * 16 bit-samples**	RETURNED VALUE		:	None**	COMMENTS			:	- Buffer_in shall be ordered by 
* 						sensitivity classes :
*							Class 0
*							Class 1
*							Class 2
*							8 CRC bits
*							4 zeroes
*						- Buffer_out :
*							0 --> +127
*							1 --> -127
*							Class 0 (not encoded)
*							Class 1 (8/12 encoded)
*							Class 2 (8/18 encoded)
*							8 CRC bits (8/18 encoded)
*							4 zeroes (8/18 encoded)
*
**************************************************************************/

void	Rcpc_Coding(Word16 FS_Flag, Word16 Input_Frame[],
			Word16 Output_Frame[])
{
/* Variables */
Word16             i, temp, Msb_bit_div2;
Word16             Nber_coded_bits;
Word16             Index_puncturing;
Word16             Coder_state;
Word16             Lsb;
Word16             Size_Class0, Size_Class1, Size_Class2, Size_Error_Control;     

if (!FS_Flag) {
Size_Class0 = N0_2;
Size_Class1 = N1_2;
Size_Class2 = N2_2;
Size_Error_Control = SIZE_CRC;

} /* If FS_Flag */
else {
Size_Class0 = N0;
Size_Class1 = N1;
Size_Class2 = N2;
Size_Error_Control = Fs_SIZE_CRC;
}

/* Recopy of Class 0 (unprotected) */
for (i = 0; i < Size_Class0; i++)
	Output_Frame[i] = Input_Frame[i];

/* Init of the Starting State of the encoder at zero */
Coder_state = 0;
/* Init Number of Coded Bits */
Nber_coded_bits = 0;  

Msb_bit_div2 = shr( Msb_bit,(Word16)1 );

/*-------------------------------------------------------------------------*/
/* Coding of Class 1 */

/* Init of Index for Puncturing: 0 <= Index_puncturing < Period_pct */
Index_puncturing = 0;

for (i = 0; i < Size_Class1; i++) {   /* Loop on class 1 */
/* Output Bit (LSB of the previous state), to define the transition number */
	Lsb = Coder_state & 1;
/* Change of state : New state of the encoder */
	temp = extract_l(L_mult(Msb_bit_div2,Input_Frame[Size_Class0 + i]));
	Coder_state = add( temp,shr( Coder_state,(Word16)1 ) );

/* According to the Puncturing matrix, computation of a coded bit */
/* First coded bit, if any, per info bit */
#ifdef DEBUG        
	if ((A1[Index_puncturing]) != 0)  
		{
#endif
		Output_Frame[Size_Class0 + Nber_coded_bits] = (T1[Coder_state][Lsb] > 0) ? -127 : 127;
		Nber_coded_bits++;
#ifdef DEBUG                
		}
#endif
/* Second coded bit, if any, per info bit */
	if ((A1[Index_puncturing + Period_pct]) != 0) 
		{
		Output_Frame[Size_Class0 + Nber_coded_bits] = (T2[Coder_state][Lsb] > 0) ? -127 : 127;
		Nber_coded_bits++;
		}
#ifdef DEBUG
/* Third coded bit, if any, per info bit */
	if ((A1[Index_puncturing + 2*Period_pct]) != 0) 
		{
		Output_Frame[Size_Class0 + Nber_coded_bits] = (T3[Coder_state][Lsb] > 0) ? -127 : 127;
		Nber_coded_bits++;
		}
#endif
	Index_puncturing++;
	if (sub( Index_puncturing,(Word16)Period_pct ) == 0)
		Index_puncturing = 0;
} /* End Loop on class 1 */
/* End coding class 1 */
/*-------------------------------------------------------------------------*/
/*-------------------------------------------------------------------------*/
/* Coding of Class 2 */

/* Init of Index for Puncturing: 0 <= Index_puncturing < Period_pct */
Index_puncturing = 0;

for (i = 0; i < Size_Class2 + Size_Error_Control + (K - 1); i++) {   /* Loop on class 2 */
/* Output Bit (LSB of the previous state), to define the transition number */
	Lsb = Coder_state & 1;
/* Change of state : New state of the encoder */
	temp = extract_l(L_mult(Msb_bit_div2,Input_Frame[Size_Class0 + Size_Class1 + i]));
	Coder_state = add( temp,shr( Coder_state,(Word16)1 ) );

/* According to the Puncturing matrix, computation of a coded bit */
/* First coded bit, if any, per info bit */
#ifdef DEBUG        
	if ((A2[Index_puncturing]) != 0)  
		{
#endif                
		Output_Frame[Size_Class0 + Nber_coded_bits] = (T1[Coder_state][Lsb] > 0) ? -127 : 127;
		Nber_coded_bits++;
#ifdef DEBUG        
		}
#endif

/* Second coded bit, if any, per info bit */
#ifdef DEBUG        
	if ((A2[Index_puncturing + Period_pct]) != 0) 
		{
#endif
		Output_Frame[Size_Class0 + Nber_coded_bits] = (T2[Coder_state][Lsb] > 0) ? -127 : 127;
		Nber_coded_bits++;
#ifdef DEBUG        
		}
#endif

if (!FS_Flag) {        
	if ((A2[Index_puncturing + 2*Period_pct]) != 0) 
/* Third coded bit, if any, per info bit */
		{
		Output_Frame[Size_Class0 + Nber_coded_bits] = (T3[Coder_state][Lsb] > 0) ? -127 : 127;
		Nber_coded_bits++;
		}
} /* If FS_Flag */
else {
	if ((Fs_A2[Index_puncturing + 2*Period_pct]) != 0) 
/* Third coded bit, if any, per info bit */
		{
		Output_Frame[Size_Class0 + Nber_coded_bits] = (T3[Coder_state][Lsb] > 0) ? -127 : 127;
		Nber_coded_bits++;
		}
}


	Index_puncturing++;
	if (sub( Index_puncturing,(Word16)Period_pct ) == 0)
		Index_puncturing = 0;

} /* End Loop on class 2 */

/* End coding class 2 */
/*-------------------------------------------------------------------------*/
}


/**************************************************************************
*
*	ROUTINE				:	Transform_Class_0
*
*	DESCRIPTION			:	Transformation ("encoding") of class 0 of the frame
*						0 --> +127
*						1 --> -127
*						the remaining of the frame is not modified
*
**************************************************************************
*
*	USAGE				:	Transform_Class_0(flag,buffer)
*							(Routine_Name(arg1,arg2))
*
*	ARGUMENT(S)			:	
*
*		ARG1				:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*						- Format : Word16**		ARG2				:	- Description : Frame to be encoded*							- Format : 286 * 16 bit-samples**	RETURNED VALUE		:	None**	COMMENTS			:	Class 0 corresponds to the N0_2 first bits*						of the buffer (N0 in case of stealing)
*
**************************************************************************/

void	Transform_Class_0(Word16 FS_Flag, Word16 Input_Frame[])
{
/* Variables */
Word16          i;
Word16          Size_Class0;        

if (!FS_Flag) 
	Size_Class0 = N0_2;
else 
	Size_Class0 = N0;

for (i = 0; i < Size_Class0; i++) {

	if (Input_Frame[i] == 0)
		Input_Frame[i] = 127;
	else 
		Input_Frame[i] = -127;

} /* End Loop Size_Class0 */
}


/**************************************************************************
*
*	ROUTINE				:	Write_Tetra_File
*
*	DESCRIPTION			:	Writes a file in the TETRA hardware test
*							frame format
*
**************************************************************************
*
*	USAGE				:	Write_Tetra_File(file_pointer,buffer)
*							(Routine_Name(input1,input2))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : File pointer on output file
*							- Format : FILE
*
*		INPUT2			:	- Description : buffer containing the TETRA frame
*							- Format : 432 * 16 bit-samples
*
*	RETURNED VALUE		:	0 if process correct, -1 if EOF
*
*	COMMENTS			:	Data written in the output file are short integers
*
**************************************************************************/

short           Write_Tetra_File (FILE *fout, short *array)
{
	static short    initial = 0;
	static short    block[690];    /* 960 if FFFF filling is included */
	short          *ptr_block;
	short i;

/* Return value: -1  EOF
 *                0  array TETRA frame written to 'fout'
 */
                 

	/* if first call to this routine, then set up output block */
        if (initial == 0)
          {     
                initial = 1;
                ptr_block = block;
                *ptr_block++ = 0x6b21;
		for (i = 0; i < 114; i++)
			*ptr_block++ = 0; 
		/* for (i = 0; i < 45; i++)
			*ptr_block++ = 0xFFFF;  */
                *ptr_block++ = 0x6b22;
		for (i = 0; i < 114; i++)
			*ptr_block++ = 0; 
		/* for (i = 0; i < 45; i++)
			*ptr_block++ = 0xFFFF;  */
                *ptr_block++ = 0x6b23;
		for (i = 0; i < 114; i++)
			*ptr_block++ = 0; 
		/* for (i = 0; i < 45; i++)
			*ptr_block++ = 0xFFFF;  */
                *ptr_block++ = 0x6b24;
		for (i = 0; i < 114; i++)
			*ptr_block++ = 0; 
		/* for (i = 0; i < 45; i++)
			*ptr_block++ = 0xFFFF;  */
                *ptr_block++ = 0x6b25;
		for (i = 0; i < 114; i++)
			*ptr_block++ = 0; 
		/* for (i = 0; i < 45; i++)
			*ptr_block++ = 0xFFFF;  */
                *ptr_block++ = 0x6b26;
		for (i = 0; i < 114; i++)
			*ptr_block++ = 0; 
		/* for (i = 0; i < 45; i++)
			*ptr_block++ = 0xFFFF;  */
          }         
                
/* Fill first valid block */

		ptr_block = block+1;

		for (i = 0; i < 114; i++)
			 *ptr_block++ = *array++ & 0x00FF;

/* Fill second valid block */

		ptr_block = block + 161 - 45;

		for (i = 0; i < 114; i++)
			 *ptr_block++ = *array++ & 0x00FF;

/* Fill third valid block */

		ptr_block = block + 321 - 45 - 45;

		for (i = 0; i < 114; i++)
			 *ptr_block++ = *array++ & 0x00FF;

/* Fill fourth valid block */

		ptr_block = block + 481 - 45 - 45 - 45;

		for (i = 0; i < 90; i++)
			 *ptr_block++ = *array++ & 0x00FF;

/* Write out TETRA frame */
		if (fwrite (block, sizeof (short), 690, fout) != 690)
			return -1;

return 0;

}

