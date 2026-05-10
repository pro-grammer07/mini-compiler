; ModuleID = 'mini_c_subset'
source_filename = "mini_c_subset"

define i32 @sum(i32 %n) {
entry:
  %n.addr = alloca i32
  store i32 %n, ptr %n.addr
  %i = alloca i32
  store i32 0, ptr %i
  %s = alloca i32
  store i32 0, ptr %s
  %t1 = alloca i32
  store i32 0, ptr %t1
  %t2 = alloca i32
  store i32 0, ptr %t2
  %t3 = alloca i32
  store i32 0, ptr %t3
  store i32 0, ptr %s
  store i32 0, ptr %i
L1:
  %r1 = load i32, ptr %i
  %r2 = load i32, ptr %n.addr
  %r4 = icmp slt i32 %r1, %r2
  %r3 = zext i1 %r4 to i32
  store i32 %r3, ptr %t1
  %r5 = load i32, ptr %t1
  %r6 = icmp eq i32 %r5, 0
  br i1 %r6, label %L2, label %bbr7
bbr7:
  %r8 = load i32, ptr %s
  %r9 = load i32, ptr %i
  %r10 = add nsw i32 %r8, %r9
  store i32 %r10, ptr %t2
  %r11 = load i32, ptr %t2
  store i32 %r11, ptr %s
  %r12 = load i32, ptr %i
  %r13 = add nsw i32 %r12, 1
  store i32 %r13, ptr %t3
  %r14 = load i32, ptr %t3
  store i32 %r14, ptr %i
  br label %L1
L2:
  %r15 = load i32, ptr %s
  ret i32 %r15
}

define i32 @main() {
entry:
  %i = alloca i32
  store i32 0, ptr %i
  %t10 = alloca i32
  store i32 0, ptr %t10
  %t11 = alloca i32
  store i32 0, ptr %t11
  %t12 = alloca i32
  store i32 0, ptr %t12
  %t13 = alloca i32
  store i32 0, ptr %t13
  %t4 = alloca i32
  store i32 0, ptr %t4
  %t5 = alloca i32
  store i32 0, ptr %t5
  %t6 = alloca i32
  store i32 0, ptr %t6
  %t7 = alloca i32
  store i32 0, ptr %t7
  %t8 = alloca i32
  store i32 0, ptr %t8
  %t9 = alloca i32
  store i32 0, ptr %t9
  %total = alloca i32
  store i32 0, ptr %total
  %a = alloca [256 x i32]
  %_a_base = getelementptr inbounds [256 x i32], ptr %a, i32 0, i32 0
  store i32 0, ptr %i
L3:
  %r16 = load i32, ptr %i
  %r18 = icmp slt i32 %r16, 5
  %r17 = zext i1 %r18 to i32
  store i32 %r17, ptr %t4
  %r19 = load i32, ptr %t4
  %r20 = icmp eq i32 %r19, 0
  br i1 %r20, label %L4, label %bbr21
bbr21:
  %r22 = load i32, ptr %i
  %r23 = mul nsw i32 %r22, 2
  store i32 %r23, ptr %t5
  %r24 = load i32, ptr %t5
  %r25 = load i32, ptr %i
  %r26 = getelementptr inbounds i32, ptr %_a_base, i32 %r25
  store i32 %r24, ptr %r26
  %r27 = load i32, ptr %i
  %r28 = add nsw i32 %r27, 1
  store i32 %r28, ptr %t6
  %r29 = load i32, ptr %t6
  store i32 %r29, ptr %i
  br label %L3
L4:
  %r30 = call i32 @sum(i32 5)
  store i32 %r30, ptr %t7
  %r31 = load i32, ptr %t7
  store i32 %r31, ptr %total
  %r32 = load i32, ptr %total
  %r34 = icmp sgt i32 %r32, 5
  %r33 = zext i1 %r34 to i32
  store i32 %r33, ptr %t8
  %r35 = getelementptr inbounds i32, ptr %_a_base, i32 2
  %r36 = load i32, ptr %r35
  store i32 %r36, ptr %t9
  %r37 = load i32, ptr %t9
  %r39 = icmp eq i32 %r37, 4
  %r38 = zext i1 %r39 to i32
  store i32 %r38, ptr %t10
  %r40 = load i32, ptr %t8
  %r41 = load i32, ptr %t10
  %r43 = icmp ne i32 %r40, 0
  %r44 = icmp ne i32 %r41, 0
  %r45 = and i1 %r43, %r44
  %r42 = zext i1 %r45 to i32
  store i32 %r42, ptr %t11
  %r46 = load i32, ptr %t11
  %r47 = icmp eq i32 %r46, 0
  br i1 %r47, label %L5, label %bbr48
bbr48:
  %r49 = load i32, ptr %total
  %r50 = add nsw i32 %r49, 10
  store i32 %r50, ptr %t12
  %r51 = load i32, ptr %t12
  store i32 %r51, ptr %total
  br label %L6
L5:
  %r52 = load i32, ptr %total
  %r53 = sub nsw i32 %r52, 10
  store i32 %r53, ptr %t13
  %r54 = load i32, ptr %t13
  store i32 %r54, ptr %total
L6:
  %r55 = load i32, ptr %total
  ret i32 %r55
}
