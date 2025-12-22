/************************************************************************
*	FILENAME		:	sub_cd.c
*
*	DESCRIPTION		:	Sub-routines for speech channel decoding
*
************************************************************************
*
*	SUBROUTINES		:	- Bfi()
*					- Combination()
*					- Desinterleaving_Signalling()
*					- Desinterleaving_Speech()
*					- Init_Rcpc_Decoding()
*					- Rcpc_Decoding()
*					- Read_Tetra_File()
*					- Unbuild_Sensitivity_Classes()
*					- Untransform_Class_0()
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
					in the routine Rcpc_Decoding to check that the
					puncturing matrices A1 and A2 are correctly set

					The results given by this software shall be the
					same, independently of the definition of DEBUG

					The complexity of the channel decoding
					component has been evaluated with the
					assumption that DEBUG is NOT defined */


/**************************************************************************
*
*	ROUTINE				:	Bfi
*
*	DESCRIPTION			:	Computation of the Bad Frame Indicator
*							(CRC based) of a frame
*
**************************************************************************
*
*	USAGE				:	Bfi(flag,buffer)
*							(Routine_Name(arg1,arg2))
*
*	ARGUMENT(S)			:	
*
*		ARG1				:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*						- Format : Word16**	ARG2				:	- Description : One ordered frame after decoding*							- Format : Word16**	RETURNED VALUE		:	BFI = 0 --> OK*						BFI = 1 --> Bad Frame Flag set**	COMMENTS			:	8 Crc bits are located at the end  of the Input_Frame*						CRC computation is carried out on Class 2 only*						as defined by arrays TAB_CRC1 
*						(length SIZE_TAB_CRC1)
*						to TAB_CRC8 (length SIZE_TAB_CRC8)
*
**************************************************************************/

Word16     Bfi(Word16 FS_Flag, Word16 Input_Frame[])
{
/* Variables */
Word16             i, temp;
Word16             Bad_Frame_Indicator;

/* Init of the Flag */
	Bad_Frame_Indicator = 0;


if (!FS_Flag) {
	/* The class protected by the CRC (Class 2) starts at index N0_2 + N1_2 */
	
	/* First Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC1; i++)
		temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC1[i] - 1]);
	/* The CRC bit is the LSB of temp : */
	temp = temp & 1;
	/* Comparison of the CRC bit just computed to the one contained in
	the Input_Frame : */
	if (sub(temp,Input_Frame[N0_2 + N1_2 + N2_2]) != 0)
		Bad_Frame_Indicator = 1;


	/* Second Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC2; i++)
		temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC2[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0_2 + N1_2 + N2_2 + 1]) != 0)
		Bad_Frame_Indicator = 1;

	/* Third Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC3; i++)
	temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC3[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0_2 + N1_2 + N2_2 + 2]) != 0)
		Bad_Frame_Indicator = 1;

	/* Fourth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC4; i++)
		temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC4[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0_2 + N1_2 + N2_2 + 3]) != 0)
		Bad_Frame_Indicator = 1;

	/* Fifth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC5; i++)
		temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC5[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0_2 + N1_2 + N2_2 + 4]) != 0)
		Bad_Frame_Indicator = 1;

	/* Sixth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC6; i++)
		temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC6[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0_2 + N1_2 + N2_2 + 5]) != 0)
		Bad_Frame_Indicator = 1;

	/* Seventh Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC7; i++)
		temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC7[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0_2 + N1_2 + N2_2 + 6]) != 0)
		Bad_Frame_Indicator = 1;

	/* Eighth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < SIZE_TAB_CRC8; i++)
		temp = add(temp,Input_Frame[N0_2 + N1_2 + TAB_CRC8[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0_2 + N1_2 + N2_2 + 7]) != 0)
		Bad_Frame_Indicator = 1;


} /* If FS_Flag */
else {

	/* The class protected by the CRC (Class 2) starts at index N0 + N1 */

	/* First Bit of the CRC : */
	temp = 0;
	for (i = 0; i < Fs_SIZE_TAB_CRC1; i++)
		temp = add(temp,Input_Frame[N0 + N1 + Fs_TAB_CRC1[i] - 1]);
	/* The CRC bit is the LSB of temp : */
	temp = temp & 1;
	/* Comparison of the CRC bit just computed to the one contained in
	the Input_Frame : */
	if (sub(temp,Input_Frame[N0 + N1 + N2]) != 0)
		Bad_Frame_Indicator = 1;

	/* Second Bit of the CRC : */
	temp = 0;
	for (i = 0; i < Fs_SIZE_TAB_CRC2; i++)
		temp = add(temp,Input_Frame[N0 + N1 + Fs_TAB_CRC2[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0 + N1 + N2 + 1]) != 0)
		Bad_Frame_Indicator = 1;

	/* Third Bit of the CRC : */
	temp = 0;
	for (i = 0; i < Fs_SIZE_TAB_CRC3; i++)
		temp = add(temp,Input_Frame[N0 + N1 + Fs_TAB_CRC3[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0 + N1 + N2 + 2]) != 0)
		Bad_Frame_Indicator = 1;

	/* Fourth Bit of the CRC : */
	temp = 0;
	for (i = 0; i < Fs_SIZE_TAB_CRC4; i++)
		temp = add(temp,Input_Frame[N0 + N1 + Fs_TAB_CRC4[i] - 1]);
	temp = temp & 1;
	if (sub(temp,Input_Frame[N0 + N1 + N2 + 3]) != 0)
		Bad_Frame_Indicator = 1;

}

return(Bad_Frame_Indicator);
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
*	ROUTINE				:	Desinterleaving_Signalling
*
*	DESCRIPTION			:	Signalling Channel-type Desinterleaving
*						of a single frame (216 bits)
*
**************************************************************************
*
*	USAGE				:	Desinterleaving_Signalling(buffer_in,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : One interleaved frame
*							- Format : 216 * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*	OUTPUT1			:	- Description : One matrix desinterleaved frame
*							- Format : 216 * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

Word16     Desinterleaving_Signalling(Word16 Input_Frame[], 
			Word16 Output_frame[])

{
static Word16   K3_const = 216;
static Word16   K_const = 216;
static Word16   a_const = 101;
Word16  i, k;


for (i = 0; i < K3_const; i++) {
	k = (Word16)((Word32)((Word32)a_const * (Word32)(i+1)) % K_const);
	Output_frame[i] = Input_Frame[k];
}

return(0);
}


/**************************************************************************
*
*	ROUTINE				:	Desinterleaving_Speech
*
*	DESCRIPTION			:	Desinterleaving of an interleaved frame (432 bits) 
*
**************************************************************************
*
*	USAGE				:	Desinterleaving_Speech(buffer_in,buffer_out)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : One interleaved frame
*							- Format : 432 * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*	OUTPUT1			:	- Description : One matrix desinterleaved frame
*							- Format : 432 * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

Word16     Desinterleaving_Speech(Word16 Input_Frame[], 
			Word16 Output_frame[])

{
Word16             index_lines, index_columns;

for (index_columns = 0; index_columns < COLUMNS; index_columns++) {
	  for (index_lines = 0; index_lines < LINES; index_lines++)
		Output_frame[index_lines * COLUMNS + index_columns] =
			Input_Frame[index_columns * LINES + index_lines];
} /* End Loop COLUMNS */

return(0);
}


/**************************************************************************
*
*	ROUTINE				:	Init_Rcpc_Decoding
*
*	DESCRIPTION			:	Initialization for convolutional rate compatible
*							punctured decoding
*
**************************************************************************
*
*	USAGE				:	Init_Rcpc_Decoding()
*							(Routine_Name)
*
*	ARGUMENT(S)			:	None
*
*	RETURNED VALUE		:	None
*
**************************************************************************/

void	Init_Rcpc_Decoding(void)
{
/* Variables */
Word16             M;
Word16             Arrival_state;  /* index for Loop on the Lattice States */
Word16             Starting_state;
Word16             Msb;    /* Value used for computation of coded bit */
Word16             Lsb;    /* Value used for computation of coded bit */
Word16             Lsb_bits;
Word16             Msbs_starting_state;
Word16             Involved_bits;


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
		Starting_state = add(shl( Msbs_starting_state,(Word16)1 ),Lsb);
		Previous[Arrival_state][Lsb] = Starting_state;

/*   TRANSITION BITS T1, T2, T3   */
		Involved_bits = add( shl( Msb,(Word16)1 ),Starting_state );

		T1[Arrival_state][Lsb] = Combination( Involved_bits,(Word16)G1 );
		T2[Arrival_state][Lsb] = Combination( Involved_bits,(Word16)G2 );
		T3[Arrival_state][Lsb] = Combination( Involved_bits,(Word16)G3 );
	} /* End Loop on Lsb  */

} /* End Loop on Arrival_state */
}


/**************************************************************************
*
*	ROUTINE				:	Rcpc_Decoding
*
*	DESCRIPTION			:	Convolutional rate compatible punctured decoding
*							of a frame
*
**************************************************************************
*
*	USAGE				:	Rcpc_Decoding(flag,buffer_in,buffer_out)
*							(Routine_Name(input1,input2,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated
*						- Format : Word16
*
*		INPUT2			:	- Description : Frame to be decoded
*							- Format : 432 * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : Decoded frame
*							- Format : 286 * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	- Decoding of one frame : [-127 ... +127]
*							-127 : 1 almost sure
*							0    : 50% probability
*							+127 : 0 almost sure
*						- For the first bits, classical
*						  (punctured) Viterbi decoding ie one bit
*						  is decoded at a time,
*						- For the very last bits, block decoding.
*
**************************************************************************/

void	Rcpc_Decoding(Word16 FS_Flag, Word16 Input_Frame[],
		Word16 Output_Frame[])
{
/* Variables */
Word16          index, j;
Word16          Index_puncturing;
Word16          Nber_decoded_bits;
Word16          Step, Pointer; /* rank of the bit being decoded :
			 0 <= Step_bis < Nber_decoded_bits */
Word16          Step_bis, Pointer_bis; /* Step is counted modulo 'Decoding_delay' */
Word16          Decoder_ready; /* Flag for starting decoding */
Word16          Essai;
Word16          Lsb;
Word16          Chosen_score, Chosen_lsb;
Word16          Maximum; /* Best score of the current Step */
Word16          Best;
Word16          Arrival_state,  Arrival_state_sym;
Word32          L_temp;     
Word16          Size_Class0, Size_Class1, Size_Class2;
Word16          Size_Coded_Class1, Size_Coded_Class2, Size_Error_Control;


if (!FS_Flag) {
Size_Class0 = N0_2;
Size_Class1 = N1_2;
Size_Class2 = N2_2;
Size_Coded_Class1 = N1_2_coded;
Size_Coded_Class2 = N2_2_coded;
Size_Error_Control = SIZE_CRC;

} /* If FS_Flag */
else {
Size_Class0 = N0;
Size_Class1 = N1;
Size_Class2 = N2;
Size_Coded_Class1 = N1_coded;
Size_Coded_Class2 = N2_coded;
Size_Error_Control = Fs_SIZE_CRC;

}

/* Recopy of Class 0 (unprotected) */
for (j = 0; j < Size_Class0; j++)
	Output_Frame[j] = Input_Frame[j];

/* Init of Nber_decoded_bits, number of bits decoded */
Nber_decoded_bits = 0;

/* Init of Step  */
Step = -1;         /* Step < Decoding_delay */
Step_bis = -1;
Decoder_ready = 0; /* Decoder not ready yet (Step_bis < Decoding_delay) */

/* Init of the scores (scores of the current Step) */
/* Starting State 0 is favoured */
Score[0] = 0;
for (j = 1; j <= M_1; j++)
	Score[j] = - 16000;   /* M states */


/*-------------------------------------------------------------------------*/
/* Decoding of Class 1 */

/* Init of Index for Puncturing: 0 <= Index_puncturing < Period_pct */
Index_puncturing = 0;

for (index = 0; index < Size_Coded_Class1;) {   /* Loop on coded class 1 */
/* Loading of array Received with the received data after symetrization */
/* If Punctured data Received[data] = 0 else Received[data] = -(2*data - 1) */
#ifdef DEBUG        
	if ((A1[Index_puncturing]) != 0)
			{
#endif                        
			Received[0] = negate( sub( shl( Input_Frame[Size_Class0 +
				index],(Word16)1 ),(Word16)1 ) );
			index++;
#ifdef DEBUG        
			}
	else
			Received[0] = 0;
#endif        

	if ((A1[Index_puncturing + Period_pct]) != 0)
			{
			Received[1] = negate( sub( shl (Input_Frame[Size_Class0 +
				index],(Word16)1 ),(Word16)1 ) );
			index++;
			}
	else
			Received[1] = 0;

	
#ifdef DEBUG        
	if ((A1[Index_puncturing + 2*Period_pct]) != 0)
			{
			Received[2] = negate( sub( shl (Input_Frame[Size_Class0 +
				index],(Word16)1 ),(Word16)1 ) );
			index++;
			}
	else
#endif                        
			Received[2] = 0;

	Index_puncturing++;
	if (sub( Index_puncturing,(Word16)Period_pct ) == 0)
		Index_puncturing = 0;


/* Determination of the state of highest score in the current Step */
	Step++;
	Step_bis++;
	if (sub( Step,(Word16)Decoding_delay ) == 0) Step = 0;

/*   Computation of the best predecessor of each state and determination
of the best state */
	Maximum = -32768;
	for (j = 0; j <= M_1; j++)        
		Ex_score[j] = Score[j];

/* Loop on the states */
	for (Arrival_state_sym = ((M_1 + 1)/2); Arrival_state_sym <= M_1; Arrival_state_sym++) {

		for (Lsb = 0; Lsb <= 1; Lsb++) {    /* Loop on LSB */
/* For every state : Estimation of the best predecessor between
the one of LSB=0 and the one of LSB=1 */ 
			Essai = Ex_score[Previous[Arrival_state_sym][Lsb]];
/* Accumulation of the transition due to the received data */
			Essai = add( Essai,(Word16)((T1[Arrival_state_sym][Lsb] >
					0) ? Received[0] : negate(Received[0])) );
			Essai = add( Essai,(Word16)((T2[Arrival_state_sym][Lsb] >
					0) ? Received[1] : negate(Received[1])) ); 
			Essai = add( Essai,(Word16)((T3[Arrival_state_sym][Lsb] >
					0) ? Received[2] : negate(Received[2])) );

/*  Search of the best predecessor (predecessor with the highest score) */
			if (Lsb == 0) {
				Chosen_score = Essai;
				Chosen_lsb = Lsb;
			}
			else {
				if (sub(Essai,Chosen_score) > 0) {
					Chosen_score = Essai;
					Chosen_lsb = Lsb;
				}
			}

		} /* Loop on Lsb */

/* The score of the current state is the best among the two (Lsb=0,1) : */
		Score[Arrival_state_sym] = Chosen_score;
		Best_previous[Arrival_state_sym][Step] =
			Previous[Arrival_state_sym][Chosen_lsb];

/*     Search of the best arrival state */
		if (sub(Chosen_score,Maximum) > 0) {
			Best = Arrival_state_sym;
			Maximum = Chosen_score;
		}

		Arrival_state = sub( Arrival_state_sym, (Word16)((M_1 + 1)/2) );

		for (Lsb = 0; Lsb <= 1; Lsb++) {    /* Loop on LSB */
/* For every state : Estimation of the best predecessor between
the one of LSB=0 and the one of LSB=1 */ 
			Essai = Ex_score[Previous[Arrival_state][Lsb]];
/* Accumulation of the transition due to the received data */
			Essai = add( Essai,(Word16)((T1[Arrival_state][Lsb]
					> 0) ? Received[0] : negate(Received[0])) );
			Essai = add( Essai,(Word16)((T2[Arrival_state][Lsb]
					> 0) ? Received[1] : negate(Received[1])) );
			Essai = add( Essai,(Word16)((T3[Arrival_state][Lsb]
					> 0) ? Received[2] : negate(Received[2])) );

/*  Search of the best predecessor (predecessor with the highest score) */
			if (Lsb == 0) {
				Chosen_score = Essai;
				Chosen_lsb = Lsb;
			}
			else {
				if (sub(Essai,Chosen_score) > 0) {
					Chosen_score = Essai;
					Chosen_lsb = Lsb;
				}
			}

		} /* Loop on Lsb */

/* The score of the current state is the best among the two (Lsb=0,1) : */
		Score[Arrival_state] = Chosen_score;
		Best_previous[Arrival_state][Step] =
			Previous[Arrival_state][Chosen_lsb];

/*     Search of the best arrival state */
		if(sub(Chosen_score,Maximum) > 0) { 
			Best = Arrival_state;
			Maximum = Chosen_score;
		}

	} /* Loop on the states */


/* To avoid overflow, substraction of the highest score */
	for (j = 0; j <= M_1; j++)
	      Score[j] = sub(Score[j],Maximum);

/* Check that the decoder is ready */
	if (sub( Step,(Word16)(Decoding_delay - 1) ) == 0) Decoder_ready = 1;

	if (sub( Decoder_ready, (Word16)1 ) == 0) {
/* Normal procedure : decoding of one bit at a time */
			Pointer = Step;
			for (j = 1; j <= Decoding_delay - 1; j++) {
				Best =
					Best_previous[Best][Pointer];
				Pointer--;
				if (Pointer < 0)
					Pointer = Decoding_delay - 1;
			} /* End Decoding of one bit */
			L_temp = L_deposit_l(Best);
			L_temp = L_shl( L_temp,(Word16)13 );
			Output_Frame[Size_Class0 + Nber_decoded_bits] =
				extract_h(L_temp);
			Nber_decoded_bits++; 
		
/* End Normal Decoding procedure */

	} /* End if Decoder_ready */

} /* End Loop on class 1 */

/* End Decoding class 1 */
/*-------------------------------------------------------------------------*/


/*-------------------------------------------------------------------------*/
/* Decoding of Class 2 */

/* Init of Index for Puncturing: 0 <= Index_puncturing < Period_pct */
Index_puncturing = 0;

for (index = 0; index < Size_Coded_Class2; ) {   /* Loop on coded class 2 */
/* Loading of array Received with the received data after symetrization */
/* If Punctured data Received[data] = 0 else Received[data] = -(2*data - 1) */
#ifdef DEBUG        
	if ((A2[Index_puncturing]) != 0)
			{
#endif                        
			Received[0] = negate( sub( shl( Input_Frame[Size_Class0 +
				Size_Coded_Class1 + index],(Word16)1 ),(Word16)1 ) );
			index++;
#ifdef DEBUG        
			}
	else
			Received[0] = 0;
#endif

#ifdef DEBUG        
	if ((A2[Index_puncturing + Period_pct]) != 0)
			{
#endif
			Received[1] = negate( sub( shl( Input_Frame[Size_Class0 +
				Size_Coded_Class1 + index],(Word16)1 ),(Word16)1 ) );
			index++;
#ifdef DEBUG        
			}
	else
			Received[1] = 0;
#endif

	if (!FS_Flag) {                
		if ((A2[Index_puncturing + 2*Period_pct]) != 0)
			{
			Received[2] = negate( sub( shl( Input_Frame[Size_Class0 +
				Size_Coded_Class1 + index],(Word16)1 ),(Word16)1 ) );
			index++;
			}
		else
			Received[2] = 0;
	}
	else {
		if ((Fs_A2[Index_puncturing + 2*Period_pct]) != 0)
			{
			Received[2] = negate( sub( shl( Input_Frame[Size_Class0 +
				Size_Coded_Class1 + index],(Word16)1 ),(Word16)1 ) );
			index++;
			}
		else
			Received[2] = 0;
	}

	Index_puncturing++;
	if (sub( Index_puncturing,(Word16)Period_pct ) == 0)
		Index_puncturing = 0;

/* Determination of the state of highest score in the current Step */
	Step++;
	Step_bis++;
	if (sub( Step,(Word16)Decoding_delay ) == 0) Step = 0;

/*   Computation of the best predecessor of each state and determination
of the best state */
	Maximum = -32768;
	for (j = 0; j <= M_1; j++)        
		Ex_score[j] = Score[j];

/* Loop on the states */
	for (Arrival_state_sym = ((M_1 + 1)/2); Arrival_state_sym <= M_1; Arrival_state_sym++) {

/* Arrival_state_sym */
		for (Lsb = 0; Lsb <= 1; Lsb++) {    /* Loop on LSB */
/* For every state : Estimation of the best predecessor between
the one of LSB=0 and the one of LSB=1 */ 
			Essai = Ex_score[Previous[Arrival_state_sym][Lsb]];
/* Accumulation of the transition due to the received data */
			Essai = add( Essai,(Word16)((T1[Arrival_state_sym][Lsb] >
				0) ? Received[0] : negate(Received[0])) );
			Essai = add( Essai,(Word16)((T2[Arrival_state_sym][Lsb] >
				0) ? Received[1] : negate(Received[1])) ); 
			Essai = add( Essai,(Word16)((T3[Arrival_state_sym][Lsb] >
				0) ? Received[2] : negate(Received[2])) );

/*  Search of the best predecessor (predecessor with the highest score) */
			if (Lsb == 0) {
				Chosen_score = Essai;
				Chosen_lsb = Lsb;
			}
			else {
				if (sub(Essai,Chosen_score) > 0) {
					Chosen_score = Essai;
					Chosen_lsb = Lsb;
				}
			}


		} /* Loop on Lsb */

/* The score of the current state is the best among the two (Lsb=0,1) : */
		Score[Arrival_state_sym] = Chosen_score;
		Best_previous[Arrival_state_sym][Step] =
			Previous[Arrival_state_sym][Chosen_lsb];

		if (sub(Chosen_score,Maximum) > 0) {
			Best = Arrival_state_sym;
			Maximum = Chosen_score;
		}


		Arrival_state = sub( Arrival_state_sym,(Word16)((M_1 + 1)/2) );

		for (Lsb = 0; Lsb <= 1; Lsb++) {    /* Loop on LSB */
/* For every state : Estimation of the best predecessor between
the one of LSB=0 and the one of LSB=1 */ 
			Essai = Ex_score[Previous[Arrival_state][Lsb]];
/* Accumulation of the transition due to the received data */
			Essai = add( Essai,(Word16)((T1[Arrival_state][Lsb] > 0) ?
				Received[0] : negate(Received[0])) );
			Essai = add( Essai,(Word16)((T2[Arrival_state][Lsb] > 0) ?
				Received[1] : negate(Received[1])) );
			Essai = add( Essai,(Word16)((T3[Arrival_state][Lsb] > 0) ?
				Received[2] : negate(Received[2])) );

/*  Search of the best predecessor (predecessor with the highest score) */
			if (Lsb == 0) {
				Chosen_score = Essai;
				Chosen_lsb = Lsb;
			}
			else {
				if (sub(Essai,Chosen_score) > 0) {
					Chosen_score = Essai;
					Chosen_lsb = Lsb;
				}
			}

		} /* Loop on Lsb */

/* The score of the current state is the best among the two (Lsb=0,1) : */
		Score[Arrival_state] = Chosen_score;
		Best_previous[Arrival_state][Step] =
			Previous[Arrival_state][Chosen_lsb];

/*     Search of the best arrival state */
		if (sub(Chosen_score,Maximum) > 0) { 
			Best = Arrival_state;
			Maximum = Chosen_score;
		}
	} /* Loop on the states */

/* To avoid overflow, substraction of the highest score */
	for (j = 0; j <= M_1; j++)
		Score[j] = sub(Score[j],Maximum);

/* Check that the decoder is ready */
/*------------------------------------------------------------------------*/
/* For the very last bits of the frame, we make a block decoding :
   Decoding_delay bits are decoded at a time */
/*-------------------------------------------------------------------------*/
		  if (sub (Step_bis,(Word16)(Size_Class1 + Size_Class2 +
					Size_Error_Control + (K - 1) - 1) ) == 0) { 

/* At the end, we use the fact that the last state of the encoder is zero */
			Best = 0;
			Pointer_bis = Step_bis;
			Pointer = Step;
/* Block decoding : */
			for (j = 1; j <= Decoding_delay; j++) {
				L_temp = L_deposit_l(Best);
				L_temp = L_shl( L_temp,(Word16)13 );
				Output_Frame[Size_Class0 + Pointer_bis] =
					extract_h(L_temp);
				Best =
					Best_previous[Best][Pointer];
				Nber_decoded_bits++;
				Pointer_bis--;
				Pointer--;
				if (Pointer < 0)
					Pointer = Decoding_delay - 1;
			}
		Nber_decoded_bits = sub( Nber_decoded_bits,(Word16)(K - 1) );

		return;
		} /* End block decoding */
/*-------------------------------------------------------------------------*/
		else {
/* Normal procedure : decoding of one bit at a time */
			Pointer = Step;
			for (j = 1; j <= Decoding_delay - 1; j++) {
				Best =
					Best_previous[Best][Pointer];
				Pointer--;
				if (Pointer < 0)
					Pointer = Decoding_delay - 1;
			} /* End Decoding of one bit */
			L_temp = L_deposit_l(Best);
			L_temp = L_shl( L_temp,(Word16)13 );
			Output_Frame[Size_Class0 + Nber_decoded_bits] =
				extract_h(L_temp);
			Nber_decoded_bits++;
		}
/* End Normal Decoding procedure */
/* End if Decoder_ready */

} /* End Loop on class 2 */

/* End Decoding class 2 */
/*-------------------------------------------------------------------------*/
}

/**************************************************************************
*
*	ROUTINE				:	Read_Tetra_File
*
*	DESCRIPTION			:	Read a file in the TETRA hardware test
*							frame format
*
**************************************************************************
*
*	USAGE				:	Read_Tetra_File(file_pointer,buffer)
*							(Routine_Name(input1,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description : File pointer for the TETRA format file
*							- Format : FILE
*
*	OUTPUT ARGUMENT(S)		:	
*
*		OUTPUT1			:	- Description : buffer containing the TETRA frame
*							- Format : 432 * 16 bit-samples
*
*	RETURNED VALUE		:	0 if process correct, -1 if EOF
*
*	COMMENTS			:	Data read from the TETRA file are short integers
*
**************************************************************************/

short           Read_Tetra_File (FILE *fin, short *array)
{
	static short    initial = 0;
	static short    block[690];
	short          *ptr_block;
	short i; 
	short *start_of_array;

/* Return value: -1  EOF
 *                0  array filled with TETRA frame
 */
	start_of_array = array; 

	/* if first call to this routine, then skip past any header */
	if (initial == 0)
	  {     
		while (*block != 0x6b21)
		{
		if (fread (block, sizeof (short), 1, fin) != 1)
			return -1;
		}
		initial = 1;
		if (fread (block+1, sizeof (short), 689, fin) != 689)
			return -1;

	  } else    /* Read in TETRA frame */
	  {
		if (fread (block, sizeof (short), 690, fin) != 690)
			return -1;
	  }          
				


/* Copy first valid block */

		ptr_block = block+1;

		for (i = 0; i < 114; i++)
			*array++ = *ptr_block++;
		   

/* Copy second valid block */

		ptr_block = block + 161 - 45;

		for (i = 0; i < 114; i++)
			*array++ = *ptr_block++;

/* Copy third valid block */

		ptr_block = block + 321 - 45 - 45;

		for (i = 0; i < 114; i++)
			*array++ = *ptr_block++;

/* Copy fourth valid block */

		ptr_block = block + 481 - 45 - 45 - 45;

		for (i = 0; i < 90; i++)
			*array++ = *ptr_block++;

		array = start_of_array;
		for (i=0; i<432; i++)
		{   

		   if ((array[i] & 0x0080) == 0x0080)  array[i] 
						= array[i] | 0xFF00;
		   if ((array[i] > 127) || (array[i] < -127 ))
				printf("Input soft bit out of range\n");

		} 
		 
return 0;

}    


/**************************************************************************
*
*	ROUTINE				:	Unbuild_Sensitivity_Classes
*
*
*	DESCRIPTION			:	Rebuilds two concatened speech frames from a single
*							frame ordered in three sensitivity classes
*
**************************************************************************
*
*	USAGE				:	Unbuild_Sensitivity_Classes(flag,buffer_in, buffer_out)
*							(Routine_Name(input1,input2,output1))
*
*	INPUT ARGUMENT(S)		:	
*
*		INPUT1			:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*							- Format : Word16
*
*		INPUT2			:	- Description : One ordered frame
*							- Format : 274 * 16 bit-samples
*
*	OUTPUT ARGUMENT(S)		:	
*
*	OUTPUT1			:	- Description : Two concatened speech frames
*							          (length of one speech frame
*							          given by Length_vocoder_frame)
*						- Format : 274 * 16 bit-samples
*
*	RETURNED VALUE		:	None
*
*	COMMENTS			:	The way reordering is carried out is defined by
*						arrays TAB0 (length N0), TAB1 (length N1) and 
*						TAB2 (length N2)
*
************************************************************************/

Word16     Unbuild_Sensitivity_Classes(Word16 FS_Flag, Word16 Input_Frame[], Word16 Output_Frame[])
{
/* Variables */
Word16     i;

if (!FS_Flag) {

	/* Class 0 : */
	for (i = 0; i < N0; i++) {
		Output_Frame[TAB0[i] - 1] = Input_Frame[2*i];
		Output_Frame[Length_vocoder_frame + TAB0[i] - 1] =
						Input_Frame[2*i + 1];
	}

	/* Class 1 : */
	for (i = 0; i < N1; i++) {
		Output_Frame[TAB1[i] - 1] = Input_Frame[N0_2 + 2*i];
		Output_Frame[Length_vocoder_frame + TAB1[i] - 1] =
						Input_Frame[N0_2 + 2*i + 1];
	}


	/* Class 2 : */
	for (i = 0; i < N2; i++) {
		Output_Frame[TAB2[i] - 1] = Input_Frame[N0_2 + N1_2 + 2*i];
		Output_Frame[Length_vocoder_frame + TAB2[i] - 1] =
						Input_Frame[N0_2 + N1_2 + 2*i + 1];
	}

} /* If FS_Flag */
else {

	/* Class 0 : */
	for (i = 0; i < N0; i++) {
		Output_Frame[TAB0[i] - 1] = Input_Frame[i];
	}

	/* Class 1 : */
	for (i = 0; i < N1; i++) {
		Output_Frame[TAB1[i] - 1] = Input_Frame[N0 + i];
	}

	/* Class 2 : */
	for (i = 0; i < N2; i++) {
		Output_Frame[TAB2[i] - 1] = Input_Frame[N0 + N1 + i];
	}

}

return(0);
}


/**************************************************************************
*
*	ROUTINE				:	Untransform_Class_0
*
*	DESCRIPTION			:	Transformation ("decoding") of class 0 of the frame
*						127 >= x >= 0 --> 0
*						0 > x >= -127 --> 1
*						the remaining of the frame is not modified
*
**************************************************************************
*
*	USAGE				:	Untransform_Class_0(flag,buffer)
*							(Routine_Name(arg1,arg2))
*
*	ARGUMENT(S)			:	
*
*		ARG1				:	- Description :	- (flag = 0) : standard mode
*								- (flag  0) : frame stealing activated*						- Format : Word16**		ARG2				:	- Description : Ordered Frame (sensitivity classes)*							          before or after decoding*							          First bits  = class 0*									= Unprotected bits*						- Format : 286 * 16 bit-samples**	RETURNED VALUE		:	None
*
**************************************************************************/

Word16     Untransform_Class_0(Word16 FS_Flag, Word16 Input_Frame[])
{
/* Variables */
Word16          i;
Word16          Size_Class0;

if (!FS_Flag) 
	Size_Class0 = N0_2;
else
	Size_Class0 = N0;

for (i = 0; i < Size_Class0; i++) {
	if (Input_Frame[i] >= 0)
		Input_Frame[i] = 0;
	else
		Input_Frame[i] = 1;
} /* End Loop Size_Class0 */


return(0);  /* Normal completion */
}

